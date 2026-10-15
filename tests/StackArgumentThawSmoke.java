import jdk.internal.vm.Continuation;
import jdk.internal.vm.ContinuationScope;

public class StackArgumentThawSmoke {
    static final ContinuationScope SCOPE = new ContinuationScope("stack-arguments");
    static final int DEPTH = 96;
    static class Payload {
        volatile long value;
        Payload(long value) { this.value = value; }
    }
    static volatile long result;
    static long deep(int depth, long a, long b, long c, long d, long e,
                     long f, long g, long h, long i, long j,
                     Payload p, Payload q, Payload r, Payload s) {
        long before = a+b+c+d+e+f+g+h+i+j+p.value+q.value+r.value+s.value;
        long child = 0;
        if (depth > 0) {
            child = deep(depth-1, a,b,c,d,e,f,g,h,i,j,p,q,r,s);
        } else {
            Continuation.yield(SCOPE);
            Continuation.yield(SCOPE);
        }
        long after = a+b+c+d+e+f+g+h+i+j+p.value+q.value+r.value+s.value;
        if (after != before) throw new AssertionError("arguments changed across thaw at depth " + depth);
        return after + child;
    }
    public static void main(String[] args) {
        boolean gc = args.length != 0;
        for (int iteration = 0; iteration < 8; iteration++) {
            long seed = (System.nanoTime() & 0xffff) + iteration;
            Payload p=new Payload(seed+21), q=new Payload(seed+22);
            Payload r=new Payload(seed+23), s=new Payload(seed+24);
            long expected = (DEPTH+1L) * (14*seed + 55 + 90);
            result = -1;
            Continuation cont = new Continuation(SCOPE, () -> result = deep(DEPTH,
                    seed+1,seed+2,seed+3,seed+4,seed+5,
                    seed+6,seed+7,seed+8,seed+9,seed+10,p,q,r,s));
            int resumes = 0;
            while (!cont.isDone()) {
                cont.run();
                if (++resumes > 3) throw new AssertionError("unexpected extra yields");
                if (gc && !cont.isDone()) System.gc();
            }
            if (resumes != 3 || result != expected)
                throw new AssertionError("bad result: " + result + " expected " + expected + ", resumes=" + resumes);
        }
        System.out.println("PASS: recursive stack arguments, live references, return values" + (gc ? " and suspended-stack GC" : ""));
    }
}
