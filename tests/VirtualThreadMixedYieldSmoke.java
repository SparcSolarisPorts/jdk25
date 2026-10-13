import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.atomic.AtomicIntegerArray;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.LockSupport;

public class VirtualThreadMixedYieldSmoke {
    public static void main(String[] args) throws Exception {
        String pidFile = System.getProperty("mixedYield.pidFile");
        if (pidFile != null) {
            java.nio.file.Files.writeString(java.nio.file.Path.of(pidFile),
                    Long.toString(ProcessHandle.current().pid()));
        }
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
            failure.compareAndSet(null, error);
            System.err.println("UNCAUGHT: thread=" + thread.getName());
            error.printStackTrace(System.err);
        });
        Thread[] threads = new Thread[8];
        AtomicIntegerArray progress = new AtomicIntegerArray(threads.length);
        for (int t = 0; t < threads.length; t++) {
            final int seed = t;
            threads[t] = Thread.ofVirtual().start(() -> {
                try {
                    Object live = new Object();
                    int identity = System.identityHashCode(live);
                    long value = seed;
                    for (int i = 0; i < 20000; i++) {
                        long expected = (value * 31) ^ i;
                        value = expected;
                        LockSupport.parkNanos(1000);
                        if (value != expected || System.identityHashCode(live) != identity) {
                            throw new AssertionError("live value changed across park");
                        }
                        progress.set(seed, i + 1);
                    }
                } catch (Throwable e) {
                    failure.compareAndSet(null, e);
                }
            });
        }
        // Keep the original untimed joins: replacing them with timed joins
        // could hide a missed termination-latch notification.
        Thread watchdog = new Thread(() -> {
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(90);
            boolean[] recorded = new boolean[threads.length];
            try {
                while (true) {
                    Thread.sleep(5000);
                    for (int i = 0; i < threads.length; i++) {
                        System.out.println("worker=" + i + " state=" + threads[i].getState()
                                + " alive=" + threads[i].isAlive()
                                + " iterations=" + progress.get(i));
                        if (progress.get(i) == 20000 && threads[i].isAlive()
                                && !recorded[i]) {
                            recorded[i] = true;
                            dumpCompletionState(i, threads[i]);
                        }
                    }
                    if (System.nanoTime() >= deadline) {
                        for (int i = 0; i < threads.length; i++) {
                            if (threads[i].isAlive()) dumpCompletionState(i, threads[i]);
                        }
                        System.err.println("FAIL: original virtual-thread joins did not finish within 90 seconds");
                        System.exit(2);
                    }
                }
            } catch (InterruptedException finished) {
                // Main finished every original join.
            }
        }, "mixed-yield-watchdog");
        watchdog.setDaemon(true);
        watchdog.start();
        for (Thread t : threads) t.join();
        watchdog.interrupt();
        if (failure.get() != null) throw new AssertionError(failure.get());
        for (int i = 0; i < threads.length; i++) {
            if (progress.get(i) != 20000) {
                throw new AssertionError("worker " + i + " completed only " + progress.get(i));
            }
        }
        System.out.println("PASS: virtual-thread mixed yield/resume and live values");
    }
    // Diagnostic only: these field reads are not an atomic VM snapshot.
    private static void dumpCompletionState(int worker, Thread thread) {
        try {
            System.err.println("COMPLETION worker=" + worker
                    + " nanoTime=" + System.nanoTime());
            dumpFields("virtual", thread);
            Object cont = readField(thread, "cont");
            if (cont == null) return;
            dumpFields("continuation", cont);
            Object chunk = readField(cont, "tail");
            for (int depth = 0; chunk != null && depth < 8; depth++) {
                dumpFields("chunk[" + depth + "]", chunk);
                chunk = readField(chunk, "parent");
            }
        } catch (Throwable error) {
            System.err.println("STATE-DUMP-ERROR: " + error);
        }
    }

    private static Object readField(Object object, String name)
            throws ReflectiveOperationException {
        for (Class<?> type = object.getClass(); type != null; type = type.getSuperclass()) {
            try {
                var field = type.getDeclaredField(name);
                field.setAccessible(true);
                return field.get(object);
            } catch (NoSuchFieldException nextType) {
                // Find fields inherited from a base class.
            }
        }
        throw new NoSuchFieldException(object.getClass().getName() + "." + name);
    }

    private static void dumpFields(String label, Object object)
            throws ReflectiveOperationException {
        // Continuations may be subclasses. Include their base-class state,
        // but stop before inherited platform Thread fields and caches.
        for (Class<?> type = object.getClass(); type != null && type != Object.class;
                type = object instanceof Thread ? null : type.getSuperclass()) {
          for (var field : type.getDeclaredFields()) {
            if (java.lang.reflect.Modifier.isStatic(field.getModifiers())) continue;
            field.setAccessible(true);
            Object value = field.get(object);
            String description;
            if (value == null) {
                description = "null";
            } else if (field.getType().isPrimitive()) {
                description = String.valueOf(value);
            } else {
                description = value.getClass().getName() + "@"
                        + Integer.toHexString(System.identityHashCode(value));
                if (value.getClass().isArray()) {
                    description += " length=" + java.lang.reflect.Array.getLength(value);
                }
            }
            System.err.println("  " + label + "." + field.getName() + "=" + description);
          }
        }
    }

}
