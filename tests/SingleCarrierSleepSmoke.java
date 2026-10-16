import java.lang.reflect.Method;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicIntegerArray;
import java.util.concurrent.atomic.AtomicReference;
import jdk.jfr.Recording;
import jdk.jfr.consumer.RecordedEvent;
import jdk.jfr.consumer.RecordingFile;

public class SingleCarrierSleepSmoke {
    private static volatile boolean stop;
    private static volatile long sink;
    private static final int COUNT = 20;

    private static void worker(int id, CountDownLatch ready, AtomicIntegerArray cycles,
                               AtomicReference<Throwable> failure) {
        ready.countDown();
        try {
            int i = 0;
            int n = 100;
            long value = id + 1;
            while (!stop) {
                if (n <= 0) {
                    n = 100;
                    cycles.incrementAndGet(id);
                    Thread.sleep(20);
                }
                if (i > n) { i = 0; --n; }
                ++i;
                value = value * 1664525 + 1013904223;
            }
            sink = value;
        } catch (Throwable t) {
            failure.compareAndSet(null, t);
        }
    }

    public static void main(String[] args) throws Exception {
        Path recordingPath = Path.of(args[0]);
        boolean success;
        AtomicReference<Throwable> failure = new AtomicReference<>();
        AtomicIntegerArray cycles = new AtomicIntegerArray(COUNT);
        CountDownLatch ready = new CountDownLatch(COUNT);
        Thread[] threads = new Thread[COUNT];
        Method start = Thread.class.getMethod("startVirtualThread", Runnable.class);
        try (Recording recording = new Recording()) {
            recording.enable("jdk.VirtualThreadPinned").withThreshold(Duration.ZERO).withStackTrace();
            recording.setMaxSize(8 * 1024 * 1024);
            recording.start();
            try {
                for (int i = 0; i < COUNT; ++i) {
                    final int id = i;
                    threads[i] = (Thread) start.invoke(null,
                        (Runnable) () -> worker(id, ready, cycles, failure));
                }
                success = ready.await(15, TimeUnit.SECONDS);
                System.out.println("workers started=" + (COUNT - ready.getCount()) + "/" + COUNT);
                if (success) {
                    // Require every task to make progress while all tasks stay alive.
                    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
                    for (;;) {
                        boolean progressed = true;
                        for (int i = 0; i < COUNT; ++i) progressed &= cycles.get(i) >= 2;
                        if (progressed) break;
                        if (System.nanoTime() >= deadline) { success = false; break; }
                        Thread.sleep(10);
                    }
                }
                for (int i = 0; i < COUNT; ++i) {
                    System.out.println("worker=" + i + " cycles=" + cycles.get(i)
                        + " state=" + threads[i].getState());
                }
            } finally {
                stop = true;
                long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
                for (Thread thread : threads) {
                    if (thread == null) continue;
                    long millis = TimeUnit.NANOSECONDS.toMillis(deadline - System.nanoTime());
                    if (millis > 0) thread.join(millis);
                }
                recording.stop();
                recording.dump(recordingPath);
            }
        }
        List<RecordedEvent> events = RecordingFile.readAllEvents(recordingPath);
        int pins = 0;
        for (RecordedEvent event : events) {
            if (event.getEventType().getName().equals("jdk.VirtualThreadPinned")) {
                if (++pins <= 12) System.out.println(event);
            }
        }
        System.out.println("Pinned events=" + pins + " (first 12 printed)");
        Throwable t = failure.get();
        if (t != null) throw new AssertionError("worker failed", t);
        for (Thread thread : threads) {
            if (thread.isAlive()) throw new AssertionError("worker did not terminate");
        }
        if (!success) throw new AssertionError("single-carrier workers could not all start and sleep concurrently");
        System.out.println("PASS: 20 virtual workers sleep concurrently on one carrier");
    }
}
