import re
import itertools as it
import numpy as np
from math import log2 as lg2
import pandas as pd
import seaborn as sns
from collections import OrderedDict as odict
from itertools import compress

from pdb import set_trace as st

def log2(x):
    return 0.0 if x <= 0.0 else lg2(x)
       

class stream(object):
    def __init__(self, size, input_data, tokenizer=None, 
                        token_pattern=r"(?u)\b\w\w+\b", 
                        give_strings=True, lower_case=True):
        self.input_data = input_data
        self.size = size
        self.tokenizer = tokenizer
        self.token_pattern = token_pattern
        self.give_strings = give_strings
        self.lower_case = lower_case
        try:
            if isinstance(input_data, str):
                self.input_file = open(self.input_data)
                self.isfile = True
            elif isinstance(input_data, list) or isinstance(input_data, tuple):
                self.isfile = False

        except FileNotFoundError:
            self.isfile = False
            pass

        except OSError:
            self.isfile = False
            pass
            
        if size % 2 == 0:
            self.size = int(size + 1)
        else:
            self.size = int(size)
            
        if self.tokenizer is None:
            token_pattern = re.compile(self.token_pattern)
            self.tokenizer = lambda l: token_pattern.findall(l)
        

    def tokenize(self, str_list):
        assert isinstance(str_list, str)  # The input must be a raw string
        self.words = self.tokenizer(str_list.lower()
                                            if self.lower_case else str_list)
        return self

      
    def winds(self):
        
        itrs = it.tee(self.words, self.size)
        windows = [it.islice(anItr, s, None) for s, anItr in enumerate(itrs)]
        self.windows = list(zip(*windows))
        
        return self


    def __iter__(self):
        if self.isfile:
            self.buff = []
            for line in self.input_file:
                self.tokenize(' '.join(self.buff) + ' ' + line)
                if len(self.words) < self.size:
                    wind_complete = False
                    while not wind_complete:
                        self.buff += self.words
                        self.tokenize(self.input_file.readline())
                        if len(self.buff + self.words) >= self.size:
                            wind_complete = True
                    self.words = (self.buff + self.words)[:self.size]
                    
                self.buff = (self.buff + self.words)[self.size:]
                self.winds()
                for w in self.windows:
                    yield ' '.join(w) if self.give_strings else w    
        else:
            try:
                self.words
            except AttributeError:
                self.tokenize(self.input_data)
                
            self.winds()
            for w in self.windows:
                yield ' '.join(w) if self.give_strings else w


class language_env(object):
    def __init__(self, input_data, entropy_norm_size=100, tuple_size=3, zeta=-5):
        self.input_data = input_data
        self.entropy_norm_size = float(entropy_norm_size)
        self.tuple_size = tuple_size
        self.samples = stream(size=self.entropy_norm_size, 
                                            input_data=self.input_data)
        self.actions = [False] * (self.tuple_size + 1)
                        # Words selected from the tuple plus if-relation decision 
        self.zeta = zeta
        
    def P(self, w, tuples):
        """ P(X=w) """
        #return sum([1 for t in tuples if w in t])/self.entropy_norm_size
        return sum(tuples, ()).count(w) / self.entropy_norm_size
    
    def condP(self, a, b, tuples):
        """ P(a|b) = P(A=a)P(B=b)/P(B=b) """ 
        Pa = self.P(a, tuples)
        Pb = self.P(b, tuples)
        return Pa * Pb / Pb
    

    def entropy_norm(self, tuples):
        vocab = set(sum(tuples, ()))
        p = {w: self.P(w, tuples) for w in vocab}
        H_D = -sum(p[w] * log2(p[w]) for w in p.keys())
        return p, vocab, H_D


    def mmi_norm(x, y, tuples):
        """Mutual Information by Entropy norm between specific items. """
        P_ = {x: self.P(x, tuples), y: self.P(y, tuples)}
        P_xy = self.condP(x, y, tuples)
        return - P_[x] * log2(P_[x]) - P_[y] * (-P_xy * log2(P_xy))


    def set_actions(self, actions):
        assert not False in [isinstance(i, int) for i in  actions] \
                and len(actions) == len(self.actions)  # Actions must be integers
        # Words 'wi' constitute ('wi: 1 ? 0') a relation 'r' if it exists (r=1)?
        self.actions = [not not a for a in actions]  # [w1, w2,...,wn, r]


    def cmi_norm(self, query, tuples):
        """Mutual Information by Entropy norm between specific item and the D_k
            text sample. """
            P_, vocab, H_D = self.entropy_norm(tuples)
            query = list(compress(query, self.actions[:-1]))
            I_D = []  # I(D; q) =  H(D) - H(D|q)
            I_as = H_D  # I(D; q1, q2,...,qn) =  H(D) - H(D|q1) - ... - H(D|qn)
            
            for q in query:
                P_wq = odict({w + '|' + q: self.condP(w, q, tuples) 
                                                            for w in vocab})
                H_Dq = -P_[q] * sum(P_wq[pwq] * log2(P_wq[pwq]) 
                                                    for pwq in P_wq.keys())
                I_D.append((q, H_D - H_Dq)) 
                I_as -= H_Dq
            # TODO: define a,b,c,d for giving negative reward
            # if not mmi_norm(a,b) > mmi_norm(b,c) > mmi_norm(c,d):
            #       I_as = self.zeta 
            return I_D, I_as


    def __iter__(self):
        init = 0
        
        for sample in self.samples:
            tuples = stream(size=self.tuple_size, input_data=sample, 
                                                            give_strings=False)
            if init < self.entropy_norm_size / 2:
                for t in tuples: 
                
                    if init < self.entropy_norm_size / 2:
                        init += 1
                        yield self.cmi_norm(t, tuples)
                    else:
                        break
                
            else:
                #tuples = stream(size=self.tuple_size, input_data=sample, give_strings=False)
                #print(list(tuples))
                yield self.cmi_norm(list(tuples)[1 \
                                    + int(self.entropy_norm_size / 2)], tuples)


input_data = "LICENSE"
t_size = 5
N = 100
mi_ = []
Ias = []
ws_ = []

env = language_env(input_data=input_data, entropy_norm_size=150, tuple_size=t_size)
env.set_actions(np.random.choice([0, 1], 
                                 size=(t_size + 1,), 
                                 p=np.random \
                                     .dirichlet(alpha=[1, 1], 
                                                size=1)[0].tolist()).tolist())
for i, s in enumerate(env):
    #print(env.actions)
    ws_.append(" ".join(tuple(odict(s[0]))))
    mi_.append(np.std(list(odict(s[0]).values()))) #[int(1 + t_size / 2)])
    Ias.append(s[1])
    # TODO: Incorporate direction of the relation (order of actions 1,2,3)
    env.set_actions(np.random \
                      .choice([0, 1], 
                              size=(t_size + 1,), 
                              p=np.random \
                                  .dirichlet(alpha=[1, 1], 
                                             size=1)[0].tolist()).tolist())
    if i > N and N > 0: break 

info = pd.DataFrame({"tuple": ws_, "MI_avg": mi_, "Ias": Ias})

import seaborn as sns; sns.set()
import matplotlib.pyplot as plt
ax = sns.lineplot(x="tuple",  y='value', hue='variable', data=pd.melt(info, ["tuple"]))
#ax.set_xticklabels(rotation=30)
plt.xticks(rotation=90)

plt.autoscale()
plt.tight_layout()
plt.show()

