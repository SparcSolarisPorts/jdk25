/*
 * Runner preflight: prove jtreg forwards the inherited ergonomic limits.
 * @test
 * @summary Verify memory/processor defaults inside jtreg and a nested child JVM
 * @modules java.management jdk.management
 * @run main EnvironmentSmoke
 */
import java.lang.management.ManagementFactory;
import com.sun.management.HotSpotDiagnosticMXBean;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;

public class EnvironmentSmoke {
    private static void checkDefaults(String where) {
        var bean = ManagementFactory.getPlatformMXBean(HotSpotDiagnosticMXBean.class);
        long ram = Long.parseLong(bean.getVMOption("MaxRAM").getValue());
        long heap = Long.parseLong(bean.getVMOption("MaxHeapSize").getValue());
        int cpus = Runtime.getRuntime().availableProcessors();
        String inherited = System.getenv("JAVA_TOOL_OPTIONS");
        if (inherited == null || ram != 2L * 1024 * 1024 * 1024
                || heap > 600L * 1024 * 1024 || cpus != 8) {
            throw new AssertionError(where + ": limits not inherited; MaxRAM=" + ram
                    + " MaxHeapSize=" + heap + " processors=" + cpus
                    + " JAVA_TOOL_OPTIONS=" + inherited);
        }
        System.out.println("PASS: " + where + " MaxRAM=" + ram + " MaxHeapSize=" + heap + " processors=" + cpus);
    }
    public static void main(String[] args) throws Exception {
        checkDefaults(args.length == 0 ? "jtreg test VM" : "nested child VM");
        if (args.length != 0) return;
        String java = Path.of(System.getProperty("java.home"), "bin", "java").toString();
        String classes = System.getProperty("test.classes", System.getProperty("java.class.path"));
        var process = new ProcessBuilder(java, "-cp", classes, "EnvironmentSmoke", "child")
                .redirectErrorStream(true).start();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        System.out.print(output);
        if (process.waitFor() != 0 || !output.contains("PASS: nested child VM")) {
            throw new AssertionError("Nested Java process did not retain runner limits");
        }
    }
}
