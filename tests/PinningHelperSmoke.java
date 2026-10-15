import java.lang.foreign.Linker;
import java.lang.reflect.Method;
import java.time.Duration;
import java.util.ArrayList;
import java.util.concurrent.atomic.AtomicReference;
import jdk.test.lib.thread.VThreadPinner;

public class PinningHelperSmoke {
    private static final Method CARRIER;
    static {
        try {
            CARRIER = Thread.class.getDeclaredMethod("currentCarrierThread");
            CARRIER.setAccessible(true);
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }
    private static Thread carrier() throws Exception {
        return (Thread) CARRIER.invoke(null);
    }
    private static class Expected extends Exception {}
    public static void main(String[] args) throws Throwable {
        boolean jni;
        try {
            Linker.nativeLinker();
            jni = false;
        } catch (UnsupportedOperationException e) {
            jni = true;
        }
        final boolean expectJNI = jni;
        AtomicReference<Throwable> failure = new AtomicReference<>();
        var threads = new ArrayList<Thread>();
        for (int n = 0; n < 8; n++) {
            threads.add(Thread.ofVirtual().unstarted(() -> {
                try {
                    Thread identity = Thread.currentThread();
                    for (int i = 0; i < 100; i++) {
                        Expected expected = new Expected();
                        try {
                            VThreadPinner.runPinned(() -> {
                                if (!Thread.currentThread().isVirtual() || Thread.currentThread() != identity)
                                    throw new AssertionError("lost virtual-thread identity");
                                if (expectJNI && !StackWalker.getInstance(StackWalker.Option.SHOW_HIDDEN_FRAMES)
                                        .walk(s -> s.anyMatch(f -> f.getClassName().equals(VThreadPinner.class.getName())
                                                && f.getMethodName().equals("invokePinned") && f.isNativeMethod())))
                                    throw new AssertionError("no native pinning frame");
                                Thread before = carrier();
                                Thread.sleep(Duration.ofMillis(1));
                                if (carrier() != before) throw new AssertionError("pinned task migrated");
                                throw expected;
                            });
                            throw new AssertionError("lost checked exception");
                        } catch (Expected actual) {
                            if (actual != expected) throw new AssertionError("changed exception identity");
                        }
                    }
                } catch (Throwable t) {
                    failure.compareAndSet(null, t);
                }
            }));
        }
        threads.forEach(Thread::start);
        long deadline = System.nanoTime() + Duration.ofSeconds(60).toNanos();
        for (Thread t : threads) {
            long remaining = deadline - System.nanoTime();
            if (remaining <= 0 || !t.join(Duration.ofNanos(remaining)))
                throw new AssertionError("pinning workers did not finish within 60 seconds");
        }
        if (failure.get() != null) throw new AssertionError("pinning worker failed", failure.get());
        System.out.println("PASS: " + (expectJNI ? "JNI" : "FFM")
                + " pinning, virtual identity, sleep/resume and checked exceptions");
    }
}
