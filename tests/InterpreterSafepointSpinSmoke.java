import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class InterpreterSafepointSpinSmoke {
    private static volatile boolean stop;
    private static final CountDownLatch ready = new CountDownLatch(1);

    private static void spin() {
        ready.countDown();
        while (!stop) {
            // Deliberately no calls: interpreter backward-branch polling must work.
        }
    }

    public static void main(String[] args) throws Exception {
        Thread worker = new Thread(InterpreterSafepointSpinSmoke::spin, "safepoint-spin");
        worker.setDaemon(true);
        worker.start();
        if (!ready.await(5, TimeUnit.SECONDS)) {
            throw new AssertionError("Worker did not start");
        }
        try {
            for (int i = 0; i < 5; i++) {
                System.gc();
            }
        } finally {
            stop = true;
        }
        worker.join(5000);
        if (worker.isAlive()) {
            throw new AssertionError("Worker did not terminate after stop");
        }
        System.out.println("PASS: safepoints with an interpreted volatile spin loop");
    }
}
