import math

def rel(a,b):
    return abs(a-b)/max((abs(a)+abs(b))*0.5,1e-12)

def largest(obs,thr):
    best=[]
    best_spread=float("inf")
    for i in range(len(obs)):
        group=[j for j in range(len(obs)) if rel(obs[i][1],obs[j][1])<=thr]
        coherent=[j for j in group if all(rel(obs[j][1],obs[k][1])<=thr for k in group)] or [i]
        vals=[obs[j][1] for j in coherent]
        spread=(max(vals)-min(vals))/max(sum(vals)/len(vals),1e-12) if len(vals)>1 else 0.0
        if len(coherent)>len(best) or (len(coherent)==len(best) and spread<best_spread):
            best=coherent; best_spread=spread
    return best

def choose(obs,strong=0.10):
    recovery=min(0.25,max(0.20,strong*2.0))
    g=largest(obs,strong)
    if len(g)>=2:
        return "STRONG_AGREEMENT",g,strong
    g=largest(obs,recovery)
    if len(g)>=2:
        return "RECOVERED_AGREEMENT",g,recovery
    raise RuntimeError("BLOCKED_AMBIGUOUS after bounded recovery")

# strong reference
obs=[("Atlas",1500.0),("MoGeIndependent",1530.0),("DepthPro",1490.0)]
mode,g,t=choose(obs)
assert mode=="STRONG_AGREEMENT" and len(g)==3 and t==0.10

# practical runtime recovery
obs=[("Atlas",1500.0),("MoGeIndependent",1740.0),("DepthPro",2050.0)]
mode,g,t=choose(obs)
assert mode=="RECOVERED_AGREEMENT" and len(g)>=2 and abs(t-0.20)<1e-9

# gross ambiguity still fail-closed
try:
    choose([("Atlas",700.0),("MoGeIndependent",1200.0),("DepthPro",2200.0)])
except RuntimeError as e:
    assert "BLOCKED_AMBIGUOUS" in str(e)
else:
    raise AssertionError("gross disagreement must block")

print("P9_V0402_FOCAL_CONSENSUS_PASS")
