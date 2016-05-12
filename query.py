# Simple extended boolean search engine: query module
# Hussein Suleman
# 14 April 2016

import re
import math
import sys
import os

import porter

import parameters

# BRF parameters
k = 10 # Number of results returned and considered for BRF
tK = 20 # Number of terms considered for BRF
docIDs = [] # IDs of the k most popular documents returned
idfs = {} # Document frequencies for the BRF most popular terms
itfs = {} # Term frequencies for the BRF most popular terms
term_accum = {}  # Overall ranking of each term

# check parameter for collection name
if len(sys.argv)<3:
   print ("Syntax: index.py <collection> <query>")
   exit(0)

# construct collection and query
collection = sys.argv[1]
query = ''
arg_index = 2
while arg_index < len(sys.argv):
   query += sys.argv[arg_index] + ' '
   arg_index += 1

# clean query
if parameters.case_folding:
   query = query.lower ()
query = re.sub (r'[^ a-zA-Z0-9]', ' ', query)
query = re.sub (r'\s+', ' ', query)
query_words = query.split (' ')

# create accumulators and other data structures
accum = {}
filenames = []
p = porter.PorterStemmer ()

# get N
f = open (collection+"_index_N", "r")
N = eval (f.read ())
f.close ()

# get document lengths/titles
titles = {}
f = open (collection+"_index_len", "r")
lengths = f.readlines ()
f.close ()

# get index for each term and calculate similarities using accumulators
for term in query_words:
    if term != '':
        if parameters.stemming:
            term = p.stem (term, 0, len(term)-1)
        if not os.path.isfile (collection+"_index/"+term):
           continue
        f = open (collection+"_index/"+term, "r")
        lines = f.readlines ()
        idf = 1
        if parameters.use_idf:
           df = len(lines)
           idf = 1/df
           if parameters.log_idf:
              idf = math.log (1 + N/df)
        for line in lines:
            mo = re.match (r'([0-9]+)\:([0-9\.]+)', line)
            if mo:
                file_id = mo.group(1)
                tf = float (mo.group(2))
                if not file_id in accum:
                    accum[file_id] = 0
                if parameters.log_tf:
                    tf = (1 + math.log (tf))
                accum[file_id] += (tf * idf)
        f.close()

# parse lengths data and divide by |N| and get titles
for l in lengths:
   mo = re.match (r'([0-9]+)\:([0-9\.]+)\:(.+)', l)
   if mo:
      document_id = mo.group (1)
      length = eval (mo.group (2))
      title = mo.group (3)
      if document_id in accum:
         if parameters.normalization:
            accum[document_id] = accum[document_id] / length
         titles[document_id] = title

# print top k results if BRF not enabled
result = sorted (accum, key=accum.__getitem__, reverse=True)
if not parameters.BRF: # If BRF is disabled, just print the top k results as per normal
    for i in range (min (len (result), k)):
        print ("{0:10.8f} {1:5} {2}".format (accum[result[i]], result[i], titles[result[i]]))
    exit(0)
else: # 1) Take the results returned by initial query as relevant results (only top k with k being between 10 to 50 in most experiments).
    for i in range (min (len (result), k)):
        docIDs.append(result[i]) # Store the doc ids of the top k documents
    print(docIDs)

# 2)Select top 20-30 (indicative number) terms from these documents using for instance tf-idf weights.
# To get these terms I could either go through each term in every document or i could through every term's index file
# I chose the latter else i'd be duplicating code of index.py (and to avoid regexes)

indexFiles = os.listdir(collection+"_index") # Get list of all index files

for index in indexFiles:
    f = open (collection+"_index/"+index, "r")
    lines = f.readlines()
    for line in lines: # Go through all the entries in the index file
        mo = re.match (r'([0-9]+)\:([0-9\.]+)', line)
        if mo:
            file_id = mo.group(1)
            tf = float (mo.group(2))
            if not file_id in docIDs: # Skip if its not one of the files in the result set
                continue
            else:
                if not index in itfs: # Increment the term frequency by the number of times is appears in the document
                    itfs[index] = tf
                else:
                    itfs[index] = itfs[index] + tf
                if not index in idfs: # Increment the number of documents the term appears in by 1. Document frequency is local to the result set, not the entire document set
                    idfs[index] = 1
                else:
                    idfs[index] = idfs[index] + 1

# Calculate the overall "rank" of each term by tf / df
for term in itfs:
    df = 1/idfs[term]
    tf = itfs[term]

# Don't think we can just naively do this the same way he does it for documents
#    if parameters.log_idf:
#        df = math.log (1 + N/idfs[term])
#
#    if parameters.log_tf:
#        tf = (1 + math.log (tf))

    term_accum[term] = (tf * df)

# Sort the term rankings
result = sorted (term_accum, key=term_accum.__getitem__, reverse=True)

# Expand the query - add the tK most popular words from the initial set
for i in range (0, tK):
    query_words.append(result[i])

print(query_words)
