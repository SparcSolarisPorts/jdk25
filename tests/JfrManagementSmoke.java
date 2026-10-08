import java.lang.management.ManagementFactory;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import javax.management.MBeanInfo;
import javax.management.MBeanOperationInfo;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import jdk.jfr.Recording;

/** Exercises Gradle's platform-MBean initialization and JFR command metadata. */
public class JfrManagementSmoke {
    public static void main(String[] args) throws Exception {
        AtomicBoolean running = new AtomicBoolean(true);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread gc = new Thread(() -> {
            try {
                while (running.get()) {
                    byte[][] pressure = new byte[16][];
                    for (int i = 0; i < pressure.length; i++) pressure[i] = new byte[65536];
                    System.gc();
                    Thread.sleep(10);
                }
            } catch (Throwable t) { failure.set(t); }
        }, "metadata-gc");
        gc.start();
        try {
            MBeanServer server = ManagementFactory.getPlatformMBeanServer();
            ObjectName name = new ObjectName("com.sun.management:type=DiagnosticCommand");
            for (int pass = 0; pass < 200; pass++) {
                MBeanInfo info = server.getMBeanInfo(name);
                int jfr = 0;
                for (MBeanOperationInfo operation : info.getOperations()) {
                    if (operation.getName().startsWith("jfr")) {
                        jfr++;
                        if (operation.getDescriptor().getFieldValue("dcmd.name") == null)
                            throw new AssertionError("Missing command metadata: " + operation);
                    }
                }
                if (jfr < 4) throw new AssertionError("Missing JFR commands: " + jfr);
                if (pass % 20 == 0) {
                    try (Recording recording = new Recording()) {
                        recording.start();
                        recording.stop();
                    }
                }
                ManagementFactory.getOperatingSystemMXBean().getAvailableProcessors();
            }
        } finally {
            running.set(false);
            gc.join(30000);
        }
        if (gc.isAlive()) throw new AssertionError("GC worker did not stop");
        if (failure.get() != null) throw new AssertionError("GC worker failed", failure.get());
        System.out.println("PASS: platform MBean startup, JFR diagnostic metadata and concurrent GC");
    }
}
