import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import jdk.internal.org.objectweb.asm.ClassWriter;
import jdk.internal.org.objectweb.asm.ConstantDynamic;
import jdk.internal.org.objectweb.asm.Handle;
import jdk.internal.org.objectweb.asm.MethodVisitor;
import jdk.internal.org.objectweb.asm.Opcodes;

/** Check initial and cached null condy loads, including GC between loads. */
public class ConstantDynamicNullSmoke implements Opcodes {
    private static final Object VALUE = new Object();
    private static int bootstraps;

    public static Object bootstrap(MethodHandles.Lookup lookup, String name, Class<?> type) {
        bootstraps++;
        return name.equals("nullValue") ? null : VALUE;
    }

    public static void main(String[] args) throws Throwable {
        String owner = "ConstantDynamicNullGenerated";
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        writer.visit(V11, ACC_PUBLIC | ACC_SUPER, owner, null, "java/lang/Object", null);
        Handle bsm = new Handle(H_INVOKESTATIC, "ConstantDynamicNullSmoke", "bootstrap",
                "(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/Class;)Ljava/lang/Object;", false);
        for (String name : new String[] {"nullValue", "objectValue"}) {
            MethodVisitor method = writer.visitMethod(ACC_PUBLIC | ACC_STATIC, name,
                    "()Ljava/lang/Object;", null, null);
            method.visitCode();
            method.visitLdcInsn(new ConstantDynamic(name, "Ljava/lang/Object;", bsm));
            method.visitInsn(ARETURN);
            method.visitMaxs(0, 0);
            method.visitEnd();
        }
        writer.visitEnd();
        Class<?> generated = MethodHandles.lookup().defineClass(writer.toByteArray());
        MethodType signature = MethodType.methodType(Object.class);
        MethodHandle nullGetter = MethodHandles.lookup().findStatic(generated, "nullValue", signature);
        MethodHandle objectGetter = MethodHandles.lookup().findStatic(generated, "objectValue", signature);
        for (int round = 0; round < 8; round++) {
            for (int i = 0; i < 10000; i++) {
                Object nullValue = (Object) nullGetter.invokeExact();
                Object objectValue = (Object) objectGetter.invokeExact();
                if (nullValue != null) throw new AssertionError("Null condy returned a non-null reference");
                if (objectValue != VALUE) throw new AssertionError("Non-null condy lost object identity");
            }
            System.gc();
        }
        if (bootstraps != 2) throw new AssertionError("Expected 2 bootstrap calls, got " + bootstraps);
        System.out.println("PASS: 80000 null/non-null condy pairs, cache reuse and GC");
    }
}
