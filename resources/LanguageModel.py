import os
import _pickle as pickle
import re
import math
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
import pandas as pd
from copy import copy

from resources.NestedDict import NestedDict
from resources.utilities import preprocess_sentence

# TODO tf-idf? Smoothing kneser-ney

class LanguageModel:
    def __init__(self, Class, source='', N=2, words=True, stemming=True, stopword_removal=False, model_file=''):
        """
        Description:        constructor for an n-gram LanguageModel object with given parameters

        Input:
        -Class:             str, the class to which this model belongs
        -source:            str, the name of the file containing the training
                            corpus for the n-gram model
        -N:                 int, the order of the model (default: 2)
        -words:             bool, indicates whether the n-gram model is created
                            from words or characters (default: True)
        -stemming:          bool, indicates whether the words are to be stemmed (default false)
        -stopword_removal:  bool, indicates whether stopwords are not stored
                            in the language model (default: True)
        -model_file:        str, can be used instead of source, indicates the
                            filename of a previously constructed language model
                            which will be loaded if specified
        """
        self.Class = Class
        if source:
            self.words = words
            self.stemmer = PorterStemmer() if stemming else None
            self.stopwords_english = list(set(stopwords.words('english'))) if stopword_removal else None
            self.models = self.make_models(source, N)
        elif model_file:
            self.words, self.stemmer, self.stopwords_english, self.models = pickle.load(open(model_file, 'rb'))

    def __repr__(self):
        """
        Description:    function that shows the representation of the class instance

        Output:
        -object_string: string that shows the model parameters of an instance
        """
        stemming = True if self.stemmer else False
        stopword_removal = True if self.stopwords_english else False
        parameters = [self.Class, len(self.models), self.words, stemming, stopword_removal]
        object_string = 'LanguageModel(Class={}, N={}, words={}, stemming={}, stopword_removal={})'.format(*parameters)
        return object_string

    def make_models(self, filename, N):
        """
        Description:    function that constructs the n-gram model for a given order
                        and a given corpus directory

        Input:
        -filename:      str, the name of the file containing the training
                        corpus for the n-gram model
        -N:             int, the order of the model

        Output:
        -models:        list, contains n-gram models from order 1 until N, constructed
                        from text files from a corpus directory
        """
        models = [NestedDict() for _ in range(N)]
        data = pd.read_csv(filename, encoding="ISO-8859-1")
        for index, row in data.iterrows():
            line = row['text']
            line = self.apply_modifications(line)
            for j in range(1, N+1):
                for i in range(j, len(line)+1):
                    words = line[i-j:i]
                    models[j-1].add_by_path(words, 1)
        return models

    def get_relative_freq(self, models, words, alpha=1.0):
        """
        Description:    function that computes the relative frequency for a given
                        list of words
        
        Input:
        -models:        list, contains n-gram models from order 1 until N
        -words:         list, words for which the relative frequency will be computed
        -alpha:         float, the number used for additive smoothing (default: 1.0)

        Output:
        -relative_freq: float, the relative frequency of the list of words
                        according to the n-gram model
        """
        length = len(words)
        voc_size = len(models[0].values())
        if length == 1:
            relative_freq = (models[0].get_by_path(words) + alpha) / float(sum(models[0].values()) + alpha*voc_size)
        else:
            ngram_freq = models[length-1].get_by_path(words)
            n_min_one_freq = models[length-2].get_by_path(words[:-1])
            relative_freq = (ngram_freq + alpha) / float(n_min_one_freq + alpha*voc_size)
        return relative_freq

    def apply_modifications(self, sentence):
        """
        Description:    function that preprocesses sentences and applies
                        stemming and stopword removal if appropriate

        Input:
        -sentence:          str, sentence to be preprocessed

        Output:
        -sentence:          str, the preprocessed sentence
        """
        sentence = f'<s> {sentence} </s>'
        if self.stemmer:
            sentence = ' '.join([self.stemmer.stem(word) for word in sentence.split()])
        if self.words:
            sentence = sentence.split()
        # if self.stemmer:
        #     sentence = [self.stemmer.stem(word) for word in sentence]
        if self.stopwords_english:
            sentence = [word for word in sentence if word not in self.stopwords_english]
        return sentence
    
    def compute_prob(self, sentence, N=None):
        """
        Description:        function that computes the log probability of a sentence
                            for a language model

        Input:
        -sentence:          str, the sentence to be classified
        -N:                 int, if specified, uses this order of n-gram model to
                            compute the probability, else uses the max order of model (default: None)

        Output:
        -sentence_prob:     float, the log probability of the sentence
        """
        sentence = preprocess_sentence(sentence)
        sentence = self.apply_modifications(sentence)
        sentence_prob = 1
        if not N:
            N = len(self.models)
        for i in range(1, len(sentence)+1):
            words = sentence[0:i] if i-N < 0 else sentence[i-N:i]
            sentence_prob += math.log(self.get_relative_freq(self.models[:N], words))
        return sentence_prob

    def get_class(self):
        """
        Description:    returns the class of the model object

        Output:
        -self.Class:    str, class of the model
        """
        return self.Class

    def get_models(self):
        """
        Description:    returns the list of n-gram models

        Output:
        -self.models:   list, contains the n-gram models of this language model
        """
        return self.models

    def save_models(self, filename):
        """
        Description:    stores the n-gram models and parameters in a pickled file
                        that can be loaded later into a LanguageModel instance

        Input:
        -filename:      str, the name of the file in which the data will be stored
        """
        pickle.dump([self.words, self.stemmer, self.stopwords_english, self.models], open(filename, 'wb'))