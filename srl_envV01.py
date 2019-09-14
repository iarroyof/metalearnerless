from srl_env_class import textEnv
import itertools
import random, csv
import numpy as np
import pandas as pd
from dask import dataframe as dd
import tensorflow as tf
import os, re, random, math
import matplotlib
matplotlib.use
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import logging
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from joblib import Parallel, delayed
from jellyfish import damerau_levenshtein_distance as dlbsh
from scipy.spatial.distance import directed_hausdorff as hsdff
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.feature_extraction.text import CountVectorizer

from pdb import set_trace as st

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                                        level=logging.INFO)

input_oie = "data/sim_train.txt.oie"
#fitting_sim_oie = "data/sim_train.txt.oie"
#develop_sim_oie = "data/sim_test.txt.oie"
#fitting_unr_oie = "data/dis_train.txt.oie"
#develop_unr_oie = "data/dis_test.txt.oie"
input_plain = "data/sim_train_.txt"
#fitting_sim = "data/sim_train_.txt"
#develop_sim = "data/sim_test_.txt"
#fitting_unr = "data/dis_train_.txt"
#develop_unr = "data/dis_test_.txt"

SAMPLE_SIZE = 100
perimeter = 30
N_STEPS = 200
dev_sample = 0.30
ngramr = (1, 3)
cols=['X', 'Y', 'Z']



def intersect(r, s):
        return set(r).intersection(s)

def unify(r, s):
        return set(r).union(s)

def ref_jaccard(sizes, item):
    try:
        return [i/sizes[item] for i in sizes]
    except ZeroDivisionError:
        return 0

def lev_hausdorff(A, B):
    #return max([min([dlbsh(a, b) for b in B]) for a in A])
    D = {}
    h = 0
    for a in A:
        shortest = np.inf
        for b in B:
            D[(a, b)] = dlbsh(a, b)
            if D[(a, b)] < shortest:
                shortest = D[(a, b)]
        if shortest > h:
            h = shortest

    return h

    
def dot_distance(A, B, binary=True, euclid=False):
    try:
        assert isinstance(A, str) and isinstance(B, str)
    except AssertionError:
        if np.nan in [A, B]:
            return 10000.0
        
    vectorizer = CountVectorizer(binary=binary, analyzer='char',
                                 ngram_range=ngramr)
    
    X = vectorizer.fit_transform([A, B])
    if euclid:
        return (X[0] - X[1]).dot((X[0] - X[1]).T).sum()
    else:
        return (X[0].toarray() ^ X[1].toarray()).sum()
    
def euc_hausdorff(A, B):
    discret = LabelEncoder()

    hausdorff = lambda u, v: max(hsdff(u, v)[0], hsdff(v, u)[0])
    discret.fit(A + B)
    a = discret.transform(A)
    b = discret.transform(B)
    if len(a) - len(b) < 0:
        a = a.tolist() + [-1] * abs(len(a) - len(b))
    elif len(a) - len(b) > 0:
        b = b.tolist() + [-1] * (len(a) - len(b))

    return hausdorff(np.array(a).reshape(1, -1), np.array(b).reshape(1, -1))
    
def set_valued_gaussian(S, M, sigma=1.0, metric='h'):
    if metric == 'h':
        if not(isinstance(S, list) and isinstance(M, list)):
            S = ngramer(S)
            M = ngramer(M)
        #distance = cat_hausdorff(S, M)
        distance = lev_hausdorff(S, M)
    elif metric == 'l':
        assert isinstance(S, str) and isinstance(M, str)
        distance = dlbsh(S, M)
    elif metric == 'hmm':
        distance = dot_distance(S, M, binary=True, euclid=False)
    if distance <= 1.0:
        return 1.0/(np.sqrt(2 * np.pi * sigma ** 2))
    else:
        return (1.0/(np.sqrt(2 * np.pi * sigma ** 2))) * math.exp(
                                            -distance ** 2/(2 * sigma ** 2))

def computeNab(df, ca, cb):
    list(map(intersect, df[[ca, cb]]))


def compute_set_probability(Akdf, perimeter_samples=50, sigma=5.0,
                                                        cols=['X', 'Y', 'Z']):
    try:
        assert len(Akdf.index) >= perimeter_samples, ("The number of perimeter " 
                                                "samples must be less or equal "
                                                "than the number of samples")
    except AssertionError:
        return None
            
    v = TfidfVectorizer(analyzer='char', ngram_range=ngramr)
    ngramer = v.build_analyzer()
    deps = []
    for a, b in itertools.product(*[cols] * 2):
        if not ((a, b) in deps and (b, a) in deps):
            deps.append((a, b))
            Akdf['+'.join((a, b))] = Akdf[[a, b]].apply(lambda x: ' '.join(x),
                                                          axis=1)
    prod_cols = []
    for a, b in itertools.product(*[cols + ['Y+Z', 'X+Z', 'X+Y']] * 2):
        if not ((a, b) in prod_cols or (b, a) in prod_cols):
            prod_cols.append((a, b))
            measures = []
            for _ in range(perimeter_samples):
                B = Akdf[b].sample(frac=1)
                measures.append(
                    np.vectorize(set_valued_gaussian)(
                        Akdf[a].str.lower(), B.str.lower(), sigma=sigma,
                        metric='hmm')
                )

            Akdf['$N_\sigma\{h(' + ', '.join((a, b)) + ')\}$'] = np.vstack(measures).mean(axis=0)
    return Akdf.dropna()

import random
#txt = "If you have to control for the case where k is larger than len(population)"

def rdn_partition(state):
    tokens = state.split()
    idxs = sorted(random.sample(range(1, len(tokens) - 1), 2))
    return {'X': " ".join(tokens[:idxs[0]]),
            'Y': " ".join(tokens[idxs[0]:idxs[1]]), 
            'Z': " ".join(tokens[idxs[1]:])}

def compute_mutuals(df, cols):

    patt = r'N_\\sigma\\{h\(([XYZ]\+?[XYZ]?), ([XYZ]\+?[XYZ]?)\)'
    pairs = sum([re.findall(patt, c) for c in cols], [])
    selfs = ["$N_\sigma\{h(" + ', '.join(p) + ")\}$"
                    for p in pairs if p[0] == p[1]]
    joins = [("$N_\sigma\{h(" + ', '.join(p) + ")\}$",  
              "$N_\sigma\{h(" + ', '.join([p[1], p[1]]) + ")\}$",
              "$N_\sigma\{h(" + ', '.join([p[0], p[0]]) + ")\}$")
                    for p in pairs if p[0] != p[1]]
    for s in selfs:
        try:
            df['I[h(' + ', '.join(re.findall(patt, s)[0]) + ')]'] = df[s].apply(
                                   lambda x: x * np.log2(x) if x > 0 else 0.0)
        except:
            st()
    for j in joins:
        df['I[h(' + ', '.join(re.findall(patt, j[0])[0]) + ')]'] = df[list(j)] \
                                                                .apply(
                                 lambda x: x[0] * np.log2(x[0]/(x[2] * x[1])) \
                                 if (x[2] * x[1] > 0 and x[0]/(x[2] * x[1]) > 0) \
                                    else 0.0,
                                 axis=1)

    return df[[c for c in df.columns if c.startswith('I[')]].sum().to_dict()


def compute_mi_steps(Akdf, out_csv):
    A_tau = [ #fit_sim_gs_Akdf[i:i + SAMPLE_SIZE]
            Akdf[i:i + SAMPLE_SIZE]
                for i in range(0, N_STEPS * SAMPLE_SIZE, SAMPLE_SIZE)]

    logging.info(f"Computing probabilities of random sets for {N_STEPS} steps...")
#fit_Psim_gsAks = Parallel(n_jobs=-1)(
    Psim_Aks = Parallel(n_jobs=-1)(
                    delayed(compute_set_probability)(
                        A_k, perimeter_samples=perimeter)
                                                for A_k in A_tau)
    probcs = [
        '$N_\sigma\{h(X, Y)\}$', '$N_\sigma\{h(Y, Z)\}$', '$N_\sigma\{h(X, Z)\}$',
        '$N_\sigma\{h(X, X)\}$', '$N_\sigma\{h(Y, Y)\}$', '$N_\sigma\{h(Z, Z)\}$',
        '$N_\sigma\{h(X, Y+Z)\}$', '$N_\sigma\{h(Y, X+Z)\}$',
        '$N_\sigma\{h(Z, X+Y)\}$']
    info_steps =  Parallel(n_jobs=-1)(
                    delayed(compute_mutuals)(df, probcs)
                                           for df in Psim_Aks if not df is None)
    pd.DataFrame(info_steps).to_csv(
                out_csv + "_Dk-{}_rho-{}_tau-{}_ng-{}.csv" \
                         .format(SAMPLE_SIZE, perimeter, N_STEPS, ngramr))

v = TfidfVectorizer(analyzer='char', ngram_range=ngramr)
ngramer = v.build_analyzer()
logging.info("Reading input file '{}'".format(input_oie))

gsAkdf = pd.read_csv(input_oie, delimiter='\t',
                            names=['score'] + cols)[cols]
dev_sim_gs_Akdf = gsAkdf.sample(frac=dev_sample)
fit_sim_gs_Akdf = gsAkdf.drop(dev_sim_gs_Akdf.index)
# Take N_STEPS and compute their marginal and joint informations
logging.info("Computing MI for OpenIE actions...")
compute_mi_steps(fit_sim_gs_Akdf, input_oie.split('.')[0])

t_size = 10
env = textEnv(input_file_name=input_plain, wsize=t_size, traject_length=N_STEPS, 
              n_trajects=N_TRAJECTORIES, beta_rwd=1.5, sample_size=SAMPLE_SIZE)

env.reset()
S, rt, done, _ = env.step()
A = []
logging.info("Simulating random actions for file '{}'".format(input_plain))
for t in range(N_STEPS):
    Ak = [rdn_partition(s[0]) for s in S]   
    S, rt, done, _ = env.step()
    A.append(Ak)
    if done: break

rdn_Akdf = pd.DataFrame(sum(A, []))
logging.info("Computing MI for random actions...")
compute_mi_steps(rdn_Akdf, input_plain.split('.')[0])
logging.info("Terminado..."