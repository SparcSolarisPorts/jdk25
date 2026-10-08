import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Pattern;

/** Exercise Java startup and a tiny requested thread-stack hint. */
public class SmallStackStartupSmoke {
    static String exercise(int depth) {
        if (depth != 0) return exercise(depth - 1);
        String value = new String(new char[] {'s', 'p', 'a', 'r', 'c'});
        if (!Pattern.matches("s[a-z]+", value)) throw new AssertionError("String/regex failure");
        if (!java.time.Duration.ofMillis(123).toString().equals("PT0.123S")) {
            throw new AssertionError("Duration failure");
        }
        return value;
    }

    public static void main(String[] args) throws Exception {
        if (!exercise(16).equals("sparc")) throw new AssertionError("Main-thread result");
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread t = new Thread(null, () -> {
            try {
                for (int i = 0; i < 2000; i++) {
                    if (!exercise(16).equals("sparc")) throw new AssertionError("Child result");
                }
            } catch (Throwable error) {
                failure.set(error);
            }
        }, "minimum-stack-hint", 1);
        t.start();
        t.join(30000);
        if (t.isAlive()) {
            t.interrupt();
            throw new AssertionError("Child thread timed out");
        }
        if (failure.get() != null) throw new AssertionError("Child failed", failure.get());
        System.out.println("PASS: minimum-stack startup, Java libraries and tiny stack-hint thread");
    }
}
