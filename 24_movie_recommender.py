# -*- coding: utf-8 -*-
"""24 Movie Recommender.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1E4O7mOlFpqW7w6b0RD0dJjSWyGVMqgve
"""

import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from nltk.tokenize import RegexpTokenizer
import re
import string
import random
from PIL import Image
import requests
from io import BytesIO
import matplotlib.pyplot as plt
from gensim.models import Word2Vec, KeyedVectors
from gensim.models.phrases import Phrases, Phraser
from matplotlib import pyplot


import matplotlib.pyplot as plt
from imageio import imread

from google.colab import drive
drive.mount('/content/drive')

df = pd.read_excel('./drive/MyDrive/Python/24-recommender/IMDB_Dataset.xlsx', sheet_name = 'Sheet1').drop(['Unnamed: 0'], axis = 1)
df

"""#Text Preprocessing

"""

# Function for removing ASCII characters
def _removeNonAscii(s):
    return "".join(i for i in s if  ord(i)<128)

# Function for converting to lower case
def make_lower_case(text):
    return text.lower()

# Function for removing stop words
def remove_stop_words(text):
    text = text.split()
    stops = set(stopwords.words("english"))
    text = [w for w in text if not w in stops]
    text = " ".join(text)
    return text

# Function for removing html
def remove_html(text):
    html_pattern = re.compile('<.*?>')
    return html_pattern.sub(r'', text)

# Function for removing punctuation
def remove_punctuation(text):
    tokenizer = RegexpTokenizer(r'\w+')
    text = tokenizer.tokenize(text)
    text = " ".join(text)
    return text

df['Cleaned'] = df['Description'].apply(_removeNonAscii)
df['Cleaned'] = df.Cleaned.apply(func = make_lower_case)
df['Cleaned'] = df.Cleaned.apply(func = remove_stop_words)
df['Cleaned'] = df.Cleaned.apply(func = remove_punctuation)
df['Cleaned'] = df.Cleaned.apply(func = remove_html)

"""# Recommendation Engine

# Word2vec model.
"""

#Models creation

# Splitting the description into words

corpus = []
for words in df['Cleaned']:
    corpus.append(words.split())


from gensim.test.utils import common_texts
from gensim.models import Word2Vec

base_model = Word2Vec(sentences=corpus, vector_size=300, window=5, min_count=1, workers=4)
base_model.train(corpus, total_examples=len(corpus), epochs=10)

#If we want to use a pretrained model and fine tune it, we can use Google News and load it in w2v_model

word2vec_path = './drive/MyDrive/Python/24-recommender/GoogleNews-vectors-negative300.bin.gz'

w2v_model = KeyedVectors.load_word2vec_format(word2vec_path, binary=True)

#Training our corpus with Google's pre-trained Word2Vec model.

fine_tuned_model = Word2Vec(sentences=corpus, vector_size=300, window=5, min_count=1, workers=4)
total_examples = fine_tuned_model.corpus_count

fine_tuned_model.build_vocab([list(w2v_model.key_to_index.keys())], update=True)
fine_tuned_model.wv.vectors_lockf = np.ones(len(fine_tuned_model.wv), dtype=np.float32)

del w2v_model
fine_tuned_model.wv.intersect_word2vec_format(word2vec_path, binary=True, lockf=1.0)

fine_tuned_model.train(corpus, total_examples=total_examples, epochs=10)

#We will create a function called vectors for generating average Word2Vec embeddings and storing them as a list called 'word_embeddings'.

def vectors(model):

    # Creating a list for storing the vectors ('Description' into vectors)
    global word_embeddings
    word_embeddings = []

    # Reading the each 'Description'
    for line in df['Cleaned']:
        avgword2vec = None
        count = 0
        for word in line.split():
            if word in model:
                count += 1
                if avgword2vec is None:
                    avgword2vec = model[word]
                else:
                    avgword2vec = avgword2vec + model[word]

        if avgword2vec is not None:
            avgword2vec = avgword2vec / count
            word_embeddings.append(avgword2vec)

#Top 5 Recommendations using Average Word2vec

# Recommending the Top 5 similar movies
def recommendations(movie):

    # Calling the function vectors
    vectors(fine_tuned_model.wv)

    # Finding cosine similarity for the vectors
    cosine_similarities = cosine_similarity(word_embeddings, word_embeddings)
    print("similarity matrix")
    print(cosine_similarities)


    # Taking the Title and Movie Image Link and store in new dataframe called 'movies'
    movies = df[['Movie', 'ImgLink']]

    # Reverse mapping of the index
    indices = pd.Series(df.index, index = df['Movie']).drop_duplicates()

    idx = indices[movie]
    sim_scores = list(enumerate(cosine_similarities[idx]))
    print()
    print("sim_scores tuples")
    print(sim_scores)
    sim_scores = sorted(sim_scores, key = lambda x: x[1], reverse = True)
    print()
    print("sorted sim_scores tuples")
    print(sim_scores)
    sim_scores = sim_scores[1:6]
    print()
    print("first 5 movies (1 to 6 because the first is the movie itself)")
    print(sim_scores)
    movie_indices = [i[0] for i in sim_scores]
    recommend = movies.iloc[movie_indices]

    for index, row in recommend.iterrows():

        url = row['ImgLink']
        try:
          img = imread(url)
          plt.figure()
          plt.imshow(img)
          plt.title(row['Movie'])
          print(row['Movie'])
        except:
          print(f"{row['Movie']} <-- Image not found")

recommendations('Avengers: Endgame')

"""
# TF-IDF Word2Vec Model"""

# Building the TF-IDF model and calculating the TF-IDF score
tfidf = TfidfVectorizer(analyzer = 'word', ngram_range = (1, 3), min_df = 5, stop_words = 'english')
tfidf.fit(df['Cleaned'])

# Getting the words from the TF-IDF model
tfidf_list = dict(zip(tfidf.get_feature_names_out(), list(tfidf.idf_)))

# TF-IDF words/column names
tfidf_feature = tfidf.get_feature_names_out()

#Building TF-IDF Word2vec Embeddings

def vectors2(model):
  global tfidf_vectors
  # Storing the TFIDF Word2Vec embeddings
  tfidf_vectors = []
  line = 0

  # For each 'Description'
  for desc in corpus:

      # Word vectors are of zero length (using 300 dimensions)
      sent_vec = np.zeros(300)

      # Number of words with a valid vector in the 'Description'
      weight_sum =0;

      # For each word in the 'Description'
      for word in desc:
          if word in model and word in tfidf_feature:
              vec = model[word]
              tf_idf = tfidf_list[word] * (desc.count(word) / len(desc))
              sent_vec += (vec * tf_idf)
              weight_sum += tf_idf
      if weight_sum != 0:
          sent_vec /= weight_sum
      tfidf_vectors.append(sent_vec)
      line += 1

#Top 5 Recommendation using TF-IDF Word2vec

# Recommending top 5 similar movies
def recommendations_2(movie):

    ### CHANGE HERE THE MODEL YOU WANT TO USE
    vectors2(fine_tuned_model.wv)

    # Finding cosine similarity for the vectors
    cosine_similarities = cosine_similarity(tfidf_vectors,  tfidf_vectors)
    print("similarity matrix")
    print(cosine_similarities)

    # Taking the Title and Image Link and store in new data frame called movies
    movies = df[['Movie', 'ImgLink']]

    # Reverse mapping of the index
    indices = pd.Series(df.index, index = df['Movie']).drop_duplicates()

    idx = indices[movie]
    sim_scores = list(enumerate(cosine_similarities[idx]))
    print()
    print("sim_scores tuples")
    print(sim_scores)
    sim_scores = sorted(sim_scores, key = lambda x: x[1], reverse = True)
    print()
    print("sorted sim_scores tuples")
    print(sim_scores)
    sim_scores = sim_scores[1:6]
    print()
    print("first 5 movies (1 to 6 because the first is the movie itself)")

    movie_indices = [i[0] for i in sim_scores]
    recommend = movies.iloc[movie_indices]

    for index, row in recommend.iterrows():

        url = row['ImgLink']
        try:
          img = imread(url)
          plt.figure()
          plt.imshow(img)
          plt.title(row['Movie'])
          print(row['Movie'])
        except:
          print(f"{row['Movie']} <-- Image not found")

recommendations_2('The Conjuring')

recommendations_2('Avengers: Endgame')