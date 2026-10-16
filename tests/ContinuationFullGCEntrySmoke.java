import jdk.internal.vm.Continuation;
import jdk.internal.vm.ContinuationScope;

public class ContinuationFullGCEntrySmoke {
    static final ContinuationScope OUTER = new ContinuationScope("outer-full-gc");
    static final ContinuationScope INNER = new ContinuationScope("inner-full-gc");
    static volatile Object garbage;
    static int checkpoints;

    static final class Payload {
        final long cookie = 0x123456789abcdef0L;
        final Payload self = this;
        final byte[] bytes = new byte[8192];
        final Object[] aliases = {this, bytes, this};
        Payload() { bytes[0] = 43; bytes[8191] = 71; }
        void check() {
            if (cookie != 0x123456789abcdef0L || self != this ||
                bytes[0] != 43 || bytes[8191] != 71 ||
                aliases[0] != this || aliases[1] != bytes || aliases[2] != this)
                throw new AssertionError("live object graph corrupted");
        }
    }

    static void makeGarbage() {
        Object[] holes = new Object[128];
        for (int i = 0; i < holes.length; i++) holes[i] = new byte[1024];
        garbage = holes;
        garbage = null;
    }

    static void inner() {
        Payload live = new Payload();
        int identity = System.identityHashCode(live);
        for (int i = 0; i < 32; i++) {
            makeGarbage();
            System.gc(); // both continuation entries are mounted GC roots
            live.check();
            if (System.identityHashCode(live) != identity)
                throw new AssertionError("identity changed");
            checkpoints++;
            if (!Continuation.yield(INNER)) throw new AssertionError("inner pinned");
            live.check();
        }
    }

    public static void main(String[] args) {
        makeGarbage();
        Continuation outer = new Continuation(OUTER, () -> {
            Payload live = new Payload();
            Continuation inner = new Continuation(INNER, ContinuationFullGCEntrySmoke::inner);
            while (!inner.isDone()) {
                inner.run();
                System.gc(); // outer mounted, inner suspended or done
                live.check();
                if (!Continuation.yield(OUTER)) throw new AssertionError("outer pinned");
            }
        });
        while (!outer.isDone()) {
            outer.run();
            System.gc(); // suspended continuation chain
        }
        if (checkpoints != 32) throw new AssertionError("checkpoints=" + checkpoints);
        System.out.println("PASS: nested mounted/suspended entries, full GC, live objects and identity");
    }
}
