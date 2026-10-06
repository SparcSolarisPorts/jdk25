import jdk.internal.vm.Continuation;
import jdk.internal.vm.ContinuationScope;
import java.util.concurrent.atomic.AtomicReference;

public class LightweightContinuationSmoke {
    private static final ContinuationScope SCOPE = new ContinuationScope("sparc-lightweight-locks");
    private static final class State {
        final Object lock = new Object();
        long sum;
        void run() {
            synchronized (lock) {
                synchronized (lock) {
                    for (int i = 0; i < 8; i++) {
                        if (!Thread.holdsLock(lock)) throw new AssertionError("lock lost before yield");
                        sum += i;
                        if (!Continuation.yield(SCOPE)) throw new AssertionError("lightweight lock pinned yield");
                        if (!Thread.holdsLock(lock)) throw new AssertionError("lock lost after remount");
                    }
                }
            }
        }
    }
    public static void main(String[] args) throws Exception {
        boolean migration = args.length != 0 && args[0].equals("migration");
        for (int round = 0; round < 100; round++) {
            State state = new State();
            Continuation c = new Continuation(SCOPE, state::run);
            int mounts = 0;
            while (!c.isDone()) {
                if (migration) {
                    AtomicReference<Throwable> failure = new AtomicReference<>();
                    Thread t = new Thread(() -> {
                        try { c.run(); } catch (Throwable ex) { failure.set(ex); }
                    });
                    t.start(); t.join(30000);
                    if (t.isAlive()) throw new AssertionError("mount timeout");
                    if (failure.get() != null) throw new AssertionError("mount failed", failure.get());
                } else {
                    c.run();
                }
                if (Thread.holdsLock(state.lock)) throw new AssertionError("carrier retained suspended lock");
                if (++mounts > 9) throw new AssertionError("too many mounts");
                System.gc();
            }
            if (mounts != 9 || state.sum != 28) throw new AssertionError("bad continuation result");
        }
        System.out.println("PASS lightweight continuation " + (migration ? "migration" : "direct"));
    }
}
