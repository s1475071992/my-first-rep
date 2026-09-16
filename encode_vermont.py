import argparse, gzip, json
import numpy as np
from sentence_transformers import SentenceTransformer


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--shard', type=int, required=True)
    ap.add_argument('--num-shards', type=int, required=True)
    ap.add_argument('--model', default='sentence-transformers/all-mpnet-base-v2')
    ap.add_argument('--batch-size', type=int, default=64)
    args=ap.parse_args()
    indices=[]; texts=[]
    with gzip.open(args.input,'rt',encoding='utf-8') as f:
        for idx,line in enumerate(f):
            if idx % args.num_shards != args.shard: continue
            row=json.loads(line)
            indices.append(idx)
            texts.append(row['text'])
    model=SentenceTransformer(args.model, device='cpu')
    emb=model.encode(texts,batch_size=args.batch_size,show_progress_bar=True,normalize_embeddings=True,convert_to_numpy=True)
    np.savez_compressed(args.output, indices=np.asarray(indices,dtype=np.int32), embeddings=emb.astype(np.float16), model_name=np.asarray(args.model))
    print({'shard':args.shard,'n':len(indices),'dim':int(emb.shape[1])})

if __name__=='__main__':
    main()
