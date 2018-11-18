from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import numpy as np
import pandas as pd
import re
from nltk import word_tokenize
from nltk.tokenize import word_tokenize
from abc import abstractmethod
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.datasets import fetch_20newsgroups
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from abc import abstractmethod
from nltk.corpus import stopwords


class SimModel:
    def __init__(self):
        pass
    
    def tokenize(self, s):
        pass
    
    @abstractmethod
    def get_features(self, inputs):
        pass
    
    def sim(self, ss):
        m = self.get_features(ss)
        sim = cosine_similarity(m, m)
        sim = (sim - np.eye(sim.shape[0]))
        return sim
    
    
class Doc2VecSimModel(SimModel):
    def infer_vector(self, s):
        s = self.tokenize(s)
        raise NotImplementedError()

    def get_features(self, inputs):
        pass
    
    def sim(self, s1, s2):
        s1 = self.tokenize(s1)
        s1 = self.tokenize(s2)
        raise NotImplementedError()


class TfIdfSimModel(SimModel):
    def __init__(self):
        self.vector = None

    def build(self):
        twenty = fetch_20newsgroups()
        vector = TfidfVectorizer(ngram_range=(1,2), max_features=20000, stop_words='english')
        vector.fit(twenty.data)
        self.vector = vector

    def get_features(self, inputs):
        if self.vector is None:
            self.build()
        return self.vector.transform(inputs)


def gensim_example():
    data = ["I love machine learning. Its awesome.",
            "I love coding in python",
            "I love building chatbots",
            "they chat amagingly well"]

    tagged_data = [TaggedDocument(words=word_tokenize(_d.lower()), tags=[str(i)]) for i, _d in enumerate(data)]
    max_epochs = 100
    vec_size = 20
    alpha = 0.025

    model = Doc2Vec(size=vec_size,
                    alpha=alpha, 
                    min_alpha=0.00025,
                    min_count=1,
                    dm =1)
    
    model.build_vocab(tagged_data)

    for epoch in range(max_epochs):
        model.train(tagged_data,
                    total_examples=model.corpus_count,
                    epochs=model.iter)
        # decrease the learning rate
        model.alpha -= 0.0002
        # fix the learning rate, no decay
        model.min_alpha = model.alpha

    model.save("temp.d2v.model")
    print("Model Saved")


def main():
    tf_model = TfIdfSimModel()
    sim = tf_model.sim(['Icon location bug is found in the index.html line 345', 
                        'I found a bug in index.html about icon', 'python end server speed is very slow when front end starts requesting'])
    print(sim)
    assert sim[0][1] > 0.3
    assert sim[0][2] < 0.3


if __name__ == '__main__':
    main()