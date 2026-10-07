import java.lang.reflect.*;
import java.util.concurrent.atomic.AtomicReference;

// Reflection keeps this test compilable by a working older boot JDK.
// Runtime needs: --add-exports java.base/jdk.internal.vm=ALL-UNNAMED
public class ContinuationSmoke {
    private static Object scope;
    private static Method yield, run, done;
    private static volatile int checkpoints;

    private static Object invoke(Method method, Object receiver, Object... args) {
        try {
            return method.invoke(receiver, args);
        } catch (InvocationTargetException e) {
            throw new AssertionError("Continuation operation failed", e.getCause());
        } catch (ReflectiveOperationException e) {
            throw new AssertionError(e);
        }
    }

    private static void body(int depth) {
        Object marker = new Object();
        Object[] live = {marker, new byte[128 * 1024]};
        long sentinel = 0x1020304050607080L ^ depth;
        if (depth > 0) {
            body(depth - 1);
        } else {
            for (int i = 0; i < 8; i++) {
                checkpoints++;
                if (!Boolean.TRUE.equals(invoke(yield, null, scope))) {
                    throw new AssertionError("Yield did not resume successfully");
                }
                if (live[0] != marker || sentinel != 0x1020304050607080L) {
                    throw new AssertionError("Live locals corrupted after resume");
                }
            }
        }
        if (live[0] != marker || sentinel != (0x1020304050607080L ^ depth)) {
            throw new AssertionError("Recursive frame locals corrupted");
        }
    }

    private static void direct(boolean migrate) throws Exception {
        Class<?> scopeClass = Class.forName("jdk.internal.vm.ContinuationScope");
        Class<?> contClass = Class.forName("jdk.internal.vm.Continuation");
        scope = scopeClass.getConstructor(String.class).newInstance("sparc-smoke");
        yield = contClass.getMethod("yield", scopeClass);
        run = contClass.getMethod("run");
        done = contClass.getMethod("isDone");
        Object cont = contClass.getConstructor(scopeClass, Runnable.class)
                .newInstance(scope, (Runnable) () -> body(12));
        for (int pass = 0; pass < 9; pass++) {
            System.out.println("ContinuationSmoke: starting pass " + pass);
            if (migrate) {
                AtomicReference<Throwable> failure = new AtomicReference<>();
                Thread carrier = new Thread(() -> {
                    try { invoke(run, cont); }
                    catch (Throwable t) { failure.set(t); }
                }, "carrier-" + pass);
                carrier.setDaemon(true);
                carrier.start();
                carrier.join(30_000);
                if (carrier.isAlive()) throw new AssertionError("Carrier did not finish within 30 seconds");
                if (failure.get() != null) throw new AssertionError(failure.get());
            } else {
                invoke(run, cont);
            }
            if (checkpoints != Math.min(pass + 1, 8)) {
                throw new AssertionError("Skipped/duplicated continuation body at pass " + pass);
            }
            if (Boolean.TRUE.equals(invoke(done, cont)) != (pass == 8)) {
                throw new AssertionError("Wrong completion state at pass " + pass);
            }
            System.out.println("ContinuationSmoke: returned pass " + pass
                    + ", checkpoints=" + checkpoints);
            System.gc(); // suspended frame oops must survive relocation
        }
        System.out.println("PASS: " + (migrate ? "carrier migration" : "yield/resume")
                + ", recursive locals, suspended-stack GC");
    }

    private static void virtual() throws Exception {
        Method start = Thread.class.getMethod("startVirtualThread", Runnable.class);
        Method isVirtual = Thread.class.getMethod("isVirtual");
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread[] threads = new Thread[32];
        for (int i = 0; i < threads.length; i++) {
            threads[i] = (Thread) invoke(start, null, (Runnable) () -> {
                try {
                    if (!Boolean.TRUE.equals(invoke(isVirtual, Thread.currentThread()))) {
                        throw new AssertionError("Not a virtual thread");
                    }
                    for (int j = 0; j < 8; j++) Thread.sleep(5);
                } catch (Throwable t) { failure.compareAndSet(null, t); }
            });
        }
        for (Thread t : threads) {
            t.join(30_000);
            if (t.isAlive()) throw new AssertionError("Virtual thread did not finish within 30 seconds");
        }
        if (failure.get() != null) throw new AssertionError(failure.get());
        System.out.println("PASS: virtual-thread creation, sleep/resume and join");
    }

    public static void main(String[] args) throws Exception {
        String mode = args.length == 0 ? "direct" : args[0];
        switch (mode) {
            case "direct": direct(false); break;
            case "migration": direct(true); break;
            case "virtual": virtual(); break;
            default: throw new IllegalArgumentException("direct | migration | virtual");
        }
    }
}
