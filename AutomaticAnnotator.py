from wit import Wit
from wrapper import *

class AutomaticAnnotator:

    def __init__(self):

        self.wit_instance = Wit(access_token="3F7OY4TME5EGYBVX4DUKRSOQDRD7XNZL")
        self.nlp = StanfordCoreNLP()


    def fixUpText(self, text):
        """This function will take a txt string and return a list of sentences in which the coreferences have been
        resolved! """

        sent_dict = self.nlp.resolve_coref(text)

        return sent_dict

    def annotateFile(self, filename):
        pass

    def annotateCorpus(self, corpusname):
        pass