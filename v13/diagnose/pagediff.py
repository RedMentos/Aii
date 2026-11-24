import sys,struct
a=open(sys.argv[1],'rb').read();b=open(sys.argv[2],'rb').read();P=4096
def hdr(d):return dict(pages=struct.unpack('>I',d[28:32])[0],counter=struct.unpack('>I',d[24:28])[0],freelist_trunk=struct.unpack('>I',d[32:36])[0],freelist_n=struct.unpack('>I',d[36:40])[0],schema_cookie=struct.unpack('>I',d[40:44])[0],wal=(d[18],d[19]),vvf=struct.unpack('>I',d[92:96])[0])
print('A',hdr(a));print('B',hdr(b))
na,nb=len(a)//P,len(b)//P
diff=[i+1 for i in range(min(na,nb)) if a[i*P:(i+1)*P]!=b[i*P:(i+1)*P]]
print('changed pages',len(diff),diff)
def kind(d,n):
  off=100 if n==1 else 0;t=d[(n-1)*P+off]
  return {2:'int-idx',5:'int-tbl',10:'leaf-idx',13:'leaf-tbl',0:'zero/free'}.get(t,hex(t))
for n in diff+list(range(na+1,nb+1)):
  off=(n-1)*P+(100 if n==1 else 0);t=b[off]
  ncell=struct.unpack('>H',b[off+3:off+5])[0]
  extra=''
  if t in (2,5):
    rc=struct.unpack('>I',b[off+8:off+12])[0];ptrs=[]
    for i in range(ncell):
      co=struct.unpack('>H',b[off+12+2*i:off+14+2*i])[0];ptrs.append(struct.unpack('>I',b[(n-1)*P+co:(n-1)*P+co+4])[0])
    extra=f' children={ptrs} right={rc}'
  print(n,'A:',kind(a,n) if n<=na else '-','B:',kind(b,n),'cells',ncell,extra)
