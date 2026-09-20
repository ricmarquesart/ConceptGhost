import hashlib, json, math

def focal_for_fov(width, deg):
    return width / (2.0 * math.tan(math.radians(deg) * 0.5))

def fov_for_focal(width, focal):
    return math.degrees(2.0 * math.atan(width / (2.0 * focal)))

def coherent_consensus(candidates, threshold=0.10):
    names=list(candidates)
    best=None
    for i,a in enumerate(names):
        for j in range(i+1,len(names)):
            b=names[j]
            av,bv=candidates[a],candidates[b]
            rel=abs(av-bv)/max((abs(av)+abs(bv))*0.5,1e-9)
            if rel <= threshold:
                cluster={a,b}
                for c in names:
                    if c in cluster: continue
                    cv=candidates[c]
                    if all(abs(cv-candidates[k])/max((abs(cv)+abs(candidates[k]))*0.5,1e-9) <= threshold for k in cluster):
                        cluster.add(c)
                score=(len(cluster),-sum(abs(candidates[x]-sum(candidates[y] for y in cluster)/len(cluster)) for x in cluster))
                if best is None or score > best[0]:
                    best=(score,cluster)
    if best is None or len(best[1]) < 2:
        raise RuntimeError("BLOCKED_AMBIGUOUS")
    src=sorted(best[1])
    return sum(candidates[x] for x in src)/len(src),src

def canonical_hash(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "cgsc_"+hashlib.sha256(raw).hexdigest()[:20]

w=1920
c={"Atlas":focal_for_fov(w,36.83),"MoGeIndependent":focal_for_fov(w,38.10),"DepthPro":focal_for_fov(w,37.40)}
f,src=coherent_consensus(c)
fov=fov_for_focal(w,f)
assert abs(fov-37.4364) < 0.03, fov
assert set(src)==set(c)

c2={"Atlas":focal_for_fov(w,55.0),"MoGeIndependent":focal_for_fov(w,37.8),"DepthPro":focal_for_fov(w,38.1)}
_,src2=coherent_consensus(c2)
assert set(src2)=={"MoGeIndependent","DepthPro"}

try:
    coherent_consensus({"Atlas":500.0,"MoGeIndependent":900.0,"DepthPro":1400.0},threshold=0.05)
except RuntimeError as e:
    assert "BLOCKED_AMBIGUOUS" in str(e)
else:
    raise AssertionError("No-cluster case must fail closed")

auto={"fov_x_deg":fov,"scale_factor":1.0,"principal_point_x_px":959.5}
manual=dict(auto); manual["fov_x_deg"]=41.0
assert manual["scale_factor"]==auto["scale_factor"]
assert manual["principal_point_x_px"]==auto["principal_point_x_px"]

contract={"schema":"ConceptGhost.P9SceneContract.v0.38.2","camera":{"fov_x_deg":41.0},"scale":{"factor":2.0},"branch":"Refined Solver Fusion"}
id1=canonical_hash(contract); id2=canonical_hash(contract)
assert id1==id2 and id1.startswith("cgsc_")

worker_fov=41.0
assert abs(worker_fov-contract["camera"]["fov_x_deg"]) < 1e-6
bad_worker_fov=40.0
assert abs(bad_worker_fov-contract["camera"]["fov_x_deg"]) > 1e-6

print("P9_CONTRACT_ACTION_PASS",id1,f"auto_fov={fov:.4f}")
