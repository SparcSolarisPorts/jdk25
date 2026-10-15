import java.time.Duration;
import java.util.Arrays;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.atomic.AtomicInteger;
import jdk.internal.vm.Continuation;
import jdk.internal.vm.ContinuationScope;

public class VirtualStackBoundarySmoke {
    static final ContinuationScope INNER = new ContinuationScope("stack-boundary-inner");
    static final int ROUNDS = 4;
    static void innerMarker(Semaphore ready, Semaphore release, AtomicInteger epoch) {
        try {
            for (int i = 0; i < ROUNDS; i++) {
                Continuation.yield(INNER);
                ready.release();
                if ((i & 1) == 0) {
                    while (epoch.get() <= i) Thread.onSpinWait();
                } else {
                    release.acquire();
                }
            }
        } catch (InterruptedException e) {
            throw new AssertionError(e);
        }
    }
    static void outerMarker(Semaphore ready, Semaphore release, AtomicInteger epoch) {
        Continuation nested = new Continuation(INNER, () -> innerMarker(ready, release, epoch));
        while (!nested.isDone()) nested.run();
    }
    static void check(boolean virtual) throws Exception {
        Semaphore ready = new Semaphore(0);
        Semaphore release = new Semaphore(0);
        AtomicInteger epoch = new AtomicInteger();
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Runnable task = () -> {
            try { outerMarker(ready, release, epoch); }
            catch (Throwable t) { failure.set(t); }
        };
        Thread worker = (virtual ? Thread.ofVirtual() : Thread.ofPlatform()).unstarted(task);
        worker.start();
        try {
            for (int i = 0; i < ROUNDS; i++) {
                if (!ready.tryAcquire(20, TimeUnit.SECONDS))
                    throw new AssertionError("worker did not reach round " + i, failure.get());
                long deadline = System.nanoTime() + Duration.ofSeconds(20).toNanos();
                Thread.State expected = ((i & 1) == 0) ? Thread.State.RUNNABLE : Thread.State.WAITING;
                while (worker.getState() != expected && System.nanoTime() < deadline) Thread.sleep(1);
                if (worker.getState() != expected)
                    throw new AssertionError("expected " + expected + ", got " + worker.getState());
                StackTraceElement[] stack = worker.getStackTrace();
                boolean inner = Arrays.stream(stack).anyMatch(f -> f.getMethodName().equals("innerMarker"));
                boolean outer = Arrays.stream(stack).anyMatch(f -> f.getMethodName().equals("outerMarker"));
                if (!inner || !outer) throw new AssertionError("lost nested/outer frames: " + Arrays.toString(stack));
                if (virtual && Arrays.stream(stack).anyMatch(f ->
                        f.getClassName().startsWith("java.util.concurrent.ForkJoin") ||
                        (f.getClassName().equals("java.lang.VirtualThread") && f.getMethodName().equals("runContinuation"))))
                    throw new AssertionError("carrier frames exposed: " + Arrays.toString(stack));
                epoch.set(i + 1);
                if ((i & 1) != 0) release.release();
            }
        } finally {
            epoch.set(Integer.MAX_VALUE);
            release.release(ROUNDS);
        }
        if (!worker.join(Duration.ofSeconds(20))) throw new AssertionError("worker did not finish");
        if (failure.get() != null) throw new AssertionError("worker failed", failure.get());
    }
    public static void main(String[] args) throws Exception {
        check(true);
        check(false);
        System.out.println("PASS: virtual carrier boundary, nested continuation frames and platform stack");
    }
}
