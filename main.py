from AutomaticAnnotator import *
from wrapper import *
import os

if __name__ == '__main__':

    path = os.path.join('stanford-corenlp-full-2016-10-31', 'patterns', 'presidents.txt')
    print(path)

    annotator = AutomaticAnnotator()

    with open(path) as file:
        text = file.read()
    print(sentdict2text(annotator.fixUpText(text)))

