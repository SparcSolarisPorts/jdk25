import jdk.internal.vm.Continuation;
import jdk.internal.vm.ContinuationScope;

// Compile/run with --add-exports java.base/jdk.internal.vm=ALL-UNNAMED.
// Use -Xcomp and a fastdebug JVM with -Xlog:continuations=trace to check
// that the execution actually reaches freeze_fast and thaw_fast.
public class ContinuationFastPath {
    static final ContinuationScope SCOPE = new ContinuationScope("sparc-fast");
    static volatile long result;
    static volatile int checkpoints;

    static long descend(int depth, long seed) {
        Object token = new Object();
        Object[] roots = {token, new byte[1024]};
        long expected = seed ^ (0x1020304050607080L + depth);
        long child = 0;
        if (depth == 0) {
            for (int i = 0; i < 4; i++) {
                checkpoints++;
                if (!Continuation.yield(SCOPE)) throw new AssertionError("yield failed");
                if (roots[0] != token || ((byte[])roots[1]).length != 1024)
                    throw new AssertionError("oop corrupted");
            }
        } else {
            child = descend(depth - 1, seed + 1);
        }
        if (roots[0] != token || expected != (seed ^ (0x1020304050607080L + depth)))
            throw new AssertionError("live locals corrupted");
        return expected + child;
    }

    static long expected(int depth, long seed) {
        long value = seed ^ (0x1020304050607080L + depth);
        return value + (depth == 0 ? 0 : expected(depth - 1, seed + 1));
    }

    public static void main(String[] args) {
        boolean gc = args.length > 0 && args[0].equals("gc");
        for (int round = 0; round < 2000; round++) {
            int depth = round % 2 == 0 ? 4 : 40; // full and partial chunk thaw
            long seed = round;
            int before = checkpoints;
            Continuation c = new Continuation(SCOPE, () -> result = descend(depth, seed));
            for (int pass = 0; pass < 5; pass++) {
                c.run();
                if (checkpoints != before + Math.min(pass + 1, 4) || c.isDone() != (pass == 4))
                    throw new AssertionError("lost/duplicated resume");
                if (gc && !c.isDone()) System.gc();
            }
            if (result != expected(depth, seed)) throw new AssertionError("return value corrupted");
        }
        System.out.println("PASS: compiled yields, full/partial thaw, live oops and return values"
                           + (gc ? ", suspended-stack GC" : ""));
    }
}
