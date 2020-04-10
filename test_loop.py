from srl_vs_rdn import SrlEnvTest
import random
import numpy as np
import pandas as pd

from pdb import set_trace as st

NACTIONS = 28561  # Number of lines in openIE input file.


def rand_ranges(a, b, N):
    j = 0
    choice = list(range(a, b))
    ranges = []
    while j < N:
        rang = np.random.choice(choice, 2, p=[1./len(choice)] * len(choice))
        if len(set(rang)) > 1:
            ranges.append(tuple(sorted(rang)))
            j += 1

    return ranges


def test_settings(n_tests, max_tests, ranges=dict(
        bias=(0.0, 10.0),
        hitmiss=(0.1, 1.0),
        bw=(1.0, 5.0),
        density=('expset', 'guasset'),
        ngrams={'low': 1, 'high': 5} )):
    """
    Generate random parameters:
        bias=3.0, hitmiss=0.3, bw=5.0,
        density='expset', ngrams={'low': 1, 'high': 5}
    """
    settings = {}
    for p, v in ranges.items():
        if not isinstance(v, dict):
            if not isinstance(v[0], str):
                settings[p] = np.random.choice(np.linspace(v[0], v[1],
                                                            max_tests),
                                 n_tests, p=[1.0/max_tests] * max_tests)
            else:
                settings[p] = np.random.choice(v, n_tests,
                                               p=[1.0/len(v)] * len(v)).tolist()
        else:
            settings[p] = rand_ranges(v['low'], v['high'], N=n_tests)
    
    for _, s in pd.DataFrame(settings).iterrows():
        yield dict(s.items())
        
        
        

def main():
    in_text = "data/dis_train_.txt"
    in_open = "data/dis_train.txt.oie"
    rdn_win = 8  # 6 + 2 (mean + std)
    sampran = (10, 30)  # sample range
    n_steps = 30
    samples = int((sampran[1] - sampran[0]) * 0.3)
    n_tests = 3

    settings = test_settings(n_tests, 80)
    
    for s in random.sample(range(sampran[0], sampran[1]), samples):
        nsteps = int(float(NACTIONS)/float(s))
        out_dir = ("../results_srl_env/wsize-"
                        + str(rdn_win) + "/sample-" + str(s))
        test = SrlEnvTest(in_oie=in_open, in_txt=in_text, output_dir=out_dir,
                        wsize=rdn_win, sample=s, nsteps=nsteps)
        for param in settings:
            test.fit(**param)


if __name__ == "__main__":
    main()
