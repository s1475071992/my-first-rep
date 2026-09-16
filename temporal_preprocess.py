import argparse, gzip, json
from collections import Counter
from datetime import datetime, timezone


def iter_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line:
                yield json.loads(line)


def kcore(rows, min_u, min_b):
    cur=list(rows)
    while True:
        uc=Counter(r['user_id'] for r in cur)
        bc=Counter(r['business_id'] for r in cur)
        nxt=[r for r in cur if uc[r['user_id']]>=min_u and bc[r['business_id']]>=min_b]
        if len(nxt)==len(cur):
            return nxt
        cur=nxt


def q(vals, p):
    if not vals: return None
    vals=sorted(vals)
    return vals[min(len(vals)-1, int((len(vals)-1)*p))]


def audit(rows):
    uc=Counter(r['user_id'] for r in rows)
    bc=Counter(r['business_id'] for r in rows)
    times=[r['time'] for r in rows]
    ratings=Counter(str(int(r['rating'])) for r in rows)
    return {
        'reviews': len(rows), 'users': len(uc), 'businesses': len(bc),
        'user_degree': {f'q{int(p*100)}': q(list(uc.values()),p) for p in [0,.25,.5,.75,.9,.95,.99,1]},
        'business_degree': {f'q{int(p*100)}': q(list(bc.values()),p) for p in [0,.25,.5,.75,.9,.95,.99,1]},
        'rating_counts': ratings,
        'time_min_ms': min(times) if times else None,
        'time_max_ms': max(times) if times else None,
        'time_min_iso': datetime.fromtimestamp(min(times)/1000, tz=timezone.utc).isoformat() if times else None,
        'time_max_iso': datetime.fromtimestamp(max(times)/1000, tz=timezone.utc).isoformat() if times else None,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--meta', required=True)
    ap.add_argument('--reviews', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--audit', required=True)
    args=ap.parse_args()

    restaurant_ids=set()
    category_examples=Counter()
    for m in iter_gz(args.meta):
        cats=m.get('category') or []
        if isinstance(cats,str): cats=[cats]
        matched=[str(c) for c in cats if 'restaurant' in str(c).lower()]
        if matched:
            restaurant_ids.add(str(m['gmap_id']))
            category_examples.update(matched)

    rows=[]
    total=0; matched_business=0; with_text=0
    for r in iter_gz(args.reviews):
        total += 1
        bid=str(r.get('gmap_id',''))
        if bid not in restaurant_ids: continue
        matched_business += 1
        text=r.get('text')
        if text is None or not str(text).strip(): continue
        with_text += 1
        try:
            row={'user_id':str(r['user_id']), 'business_id':bid, 'time':int(r['time']), 'rating':float(r['rating']), 'text':str(text)}
        except (KeyError,TypeError,ValueError):
            continue
        rows.append(row)
    rows.sort(key=lambda x:(x['time'],x['user_id'],x['business_id']))

    with gzip.open(args.output,'wt',encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r,ensure_ascii=False)+'\n')

    report={
        'source_reviews_total': total,
        'restaurant_business_ids': len(restaurant_ids),
        'restaurant_reviews_before_text_filter': matched_business,
        'restaurant_reviews_with_text': with_text,
        'top_restaurant_categories': category_examples.most_common(20),
        'raw_restaurant_text_graph': audit(rows),
        'candidate_cores': {}
    }
    for mu,mb in [(2,2),(2,5),(3,5),(3,10),(5,10),(5,20),(10,10)]:
        core=kcore(rows,mu,mb)
        report['candidate_cores'][f'u{mu}_b{mb}']=audit(core)
    with open(args.audit,'w',encoding='utf-8') as f:
        json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
