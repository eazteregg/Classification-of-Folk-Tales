import pexpect
import sys
import re
import nltk



class ProcessError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ParserError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TimeoutError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class OutOfMemoryError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def replace(referent, reference, sents_dict):
    if len(reference) != 4 or len(referent) != 4:
        raise ValueError

    # retrieve referent
    sn, start, spanx, spany = referent
    print(sents_dict[sn-1])
    referent = (sents_dict[sn-1][spanx - 1:spany - 1])

    def replacespan(sent, repl, start, end):
        first = sent[:start - 1]
        second = sent[start - 1:end - 1]
        third = sent[end - 1:]

        # adjust length of the referent string
        # if reference is longer than referent, don't resolve the coref cause reference might be holding more info
        print(repl, second)
        if len(second) > len(repl):
            return sent
        while len(second) < len(repl):
            repl.insert(0, ' '.join(repl[:2]))
            repl.pop(1)
            repl.pop(1)
        new_sent = first + repl + third
        return new_sent

    # replace reference with referent in target sent
    sm, start2, span2x, span2y = reference
    print(sents_dict[sm-1])
    sents_dict[sm-1] = replacespan(sents_dict[sm-1], referent, span2x, span2y)


def sentdict2text(sent_dict, indices=None):
    if indices:
        n, m = indices
        keys = [n, m]
    else:
        keys = sent_dict

    text = ''
    for sent in keys:
        s = ''
        for word in sent_dict[sent]:
            word = word.strip()
            if word in {'.', '\"', '!', ':', ',', '?'}:
                s = s[:-1] + word + ' '
            else:
                s += word + ' '
        text += s

    return text


def text2sentdict(text):

    # split by sentence
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    sents = tokenizer.tokenize(text)
    sents = list(filter(lambda x: len(x) > 1, sents))
    # split further by words so that the dict contains lists of words which make up the sentence
    sent_dict = {i: list(nltk.word_tokenize(sents[i].strip())) for i in range(len(sents))}

    return sent_dict


class StanfordCoreNLP:
    def __init__(self, path_to_corenlp='stanford-corenlp-full-2016-10-31/*'):
        path = 'edu.stanford.nlp.pipeline.StanfordCoreNLP'
        self.corenlp = pexpect.spawnu(
            "java -cp %s -Xmx3g %s" % (path_to_corenlp, path))
        self.corenlp.expect("Entering interactive shell.", timeout=400)
        self.corenlp.expect("\nNLP>", timeout=300)

    def interact(self, text):

        def clean_up():
            while True:
                try:
                    self.corenlp.read_nonblocking(8192, 0.1)
                except (pexpect.TIMEOUT, pexpect.EOF):
                    break

        # TIMEOUT, clean up anything left in buffer
        clean_up()

        self.corenlp.sendline(s=text)

        max_expected_time = max(300.0, len(text) / 3.0)

        t = self.corenlp.expect(['\nNLP> ', pexpect.TIMEOUT, pexpect.EOF,
                                 '\nWARNING: Parsing of sentence failed, possibly because of out of memory.'],
                                timeout=max_expected_time)
        incoming = self.corenlp.before
        if t == 1:

            print({'error': "timed out after %f seconds" % max_expected_time,
                   'input': text,
                   'output': incoming}, file=sys.stderr)
            raise TimeoutError("Timed out after %d seconds" % max_expected_time)
        elif t == 2:
            # EOF, probably crash CoreNLP process
            print({'error': "CoreNLP terminates abnormally while parsing",
                   'input': text,
                   'output': incoming}, file=sys.stderr)
            raise ProcessError("CoreNLP process terminates abnormally while parsing")
        elif t == 3:
            # out of memory
            print({'error': "WARNING: Parsing of sentence failed, possibly because of out of memory.",
                   'input': text,
                   'output': incoming}, file=sys.stderr)
            raise OutOfMemoryError

        return incoming

    def resolve_coref(self, text):
        '''Given a text, this method will analyze it and return a version where all coreferences have been resolved
        according to the Stanford Coreference Parser'''

        sent_dict = text2sentdict(text)
        text = sentdict2text(sent_dict)
        analyzed = self.interact(text)

        sentiter = re.finditer(r'Sentence #\d+ \(\d+ tokens\):\s*(.+?)\[Text', analyzed, flags=re.DOTALL)
        i=0
        sent_dict2 = dict()
        for sent in list(sentiter):
            sent_dict2[i] = nltk.tokenize.word_tokenize(sent.group(1))
            i += 1

        moiter = re.finditer(r'\s+(\(\d+,\d+,\[\d+,\d+\]\)) -> (\(\d+,\d+,\[\d+,\d+\]\))', analyzed)

        # If there are any corefs, assign them to vars
        for mo in moiter:
            mo1 = re.sub(r'[\[\]\(\)]', '', mo.group(1))
            mo2 = re.sub(r'[\[\]\(\)]', '', mo.group(2))

            # convert strings to numbers
            reference = tuple(map(lambda x: int(x), re.split(',', mo1)))
            referent = tuple(map(lambda x: int(x), re.split(',', mo2)))

            replace(referent, reference, sent_dict2)

        # No corefs means return the text as it was before
        return sent_dict2

    def kill(self):
        if self.corenlp.isalive():
            self.corenlp.close(force=True)


if __name__ == '__main__':
    nlp = StanfordCoreNLP()
    print(nlp.resolve_coref('Martin loves Julia. He loves her'))
    nlp.kill()
