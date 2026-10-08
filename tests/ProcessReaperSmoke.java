import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Bounded subprocess exits and reaper reuse, including captured output. */
public class ProcessReaperSmoke {
    private static final AtomicReference<Throwable> uncaught = new AtomicReference<>();

    public static void main(String[] args) throws Exception {
        if (!Boolean.getBoolean("jdk.lang.processReaperUseDefaultStackSize")) {
            throw new AssertionError("Default reaper stack property is not enabled");
        }
        Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
            uncaught.compareAndSet(null, error);
            error.printStackTrace(System.err);
        });
        int completed = 0;
        for (int round = 0; round < 25; round++) {
            List<Process> processes = new ArrayList<>();
            try {
                List<CompletableFuture<ProcessHandle>> exits = new ArrayList<>();
                for (int i = 0; i < 4; i++) {
                    Process p = new ProcessBuilder("/bin/sh", "-c",
                            "printf 'reaper-out\\n'; printf 'reaper-err\\n' >&2; exit 7")
                            .redirectErrorStream(true).start();
                    processes.add(p);
                    exits.add(p.toHandle().onExit());
                }
                for (int i = 0; i < processes.size(); i++) {
                    Process p = processes.get(i);
                    if (!p.waitFor(20, TimeUnit.SECONDS)) {
                        throw new AssertionError("Process waitFor timed out at round " + round);
                    }
                    ProcessHandle exited = exits.get(i).get(20, TimeUnit.SECONDS);
                    if (exited.pid() != p.pid() || p.isAlive() || p.exitValue() != 7) {
                        throw new AssertionError("Incorrect completion/exit status: pid=" + p.pid()
                                + " handle=" + exited.pid() + " alive=" + exited.isAlive()
                                + " exit=" + p.exitValue()
                                + " output=" + new String(p.getInputStream().readAllBytes()));
                    }
                    String output = new String(p.getInputStream().readAllBytes(),
                            java.nio.charset.StandardCharsets.UTF_8);
                    if (!output.equals("reaper-out\nreaper-err\n")) {
                        throw new AssertionError("Incorrect child output: " + output);
                    }
                    completed++;
                }
                if (uncaught.get() != null) {
                    throw new AssertionError("Uncaught background-thread exception", uncaught.get());
                }
            } finally {
                for (Process p : processes) {
                    if (p.isAlive()) p.destroyForcibly();
                    p.getInputStream().close();
                    p.getErrorStream().close();
                    p.getOutputStream().close();
                }
            }
        }
        System.out.println("PASS: " + completed + " subprocess exits, onExit, waitFor and output capture");
    }
}
