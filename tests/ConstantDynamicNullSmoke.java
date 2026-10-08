import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;

/** Check initial and cached null condy loads, including GC between loads. */
public class ConstantDynamicNullSmoke {
    private static final Object VALUE = new Object();
    private static int bootstraps;

    public static Object bootstrap(MethodHandles.Lookup lookup, String name, Class<?> type) {
        bootstraps++;
        return name.equals("nullValue") ? null : VALUE;
    }

    // A minimal Java 11 class file with two static ldc_w/areturn methods.
    // Use public java.io APIs so this test needs no internal ASM package.
    private static byte[] generateClass() throws IOException {
        Pool pool = new Pool();
        int owner = pool.clazz("ConstantDynamicNullGenerated");
        int parent = pool.clazz("java/lang/Object");
        int code = pool.utf8("Code");
        int bootstrapAttribute = pool.utf8("BootstrapMethods");
        int signature = pool.utf8("()Ljava/lang/Object;");
        int nullName = pool.utf8("nullValue");
        int objectName = pool.utf8("objectValue");
        int objectType = pool.utf8("Ljava/lang/Object;");
        int bootstrapOwner = pool.clazz("ConstantDynamicNullSmoke");
        int bootstrapName = pool.utf8("bootstrap");
        int bootstrapType = pool.utf8(
                "(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/Class;)Ljava/lang/Object;");
        int bootstrapRef = pool.pair(10, bootstrapOwner,
                pool.pair(12, bootstrapName, bootstrapType));
        int bootstrapHandle = pool.handle(6, bootstrapRef); // REF_invokeStatic
        int nullConstant = pool.pair(17, 0, pool.pair(12, nullName, objectType));
        int objectConstant = pool.pair(17, 0, pool.pair(12, objectName, objectType));
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        DataOutputStream out = new DataOutputStream(bytes);
        out.writeInt(0xCAFEBABE);
        out.writeShort(0); // minor
        out.writeShort(55); // Java 11: CONSTANT_Dynamic support
        out.writeShort(pool.count);
        out.write(pool.bytes.toByteArray());
        out.writeShort(0x0021); // ACC_PUBLIC | ACC_SUPER
        out.writeShort(owner);
        out.writeShort(parent);
        out.writeShort(0); // interfaces
        out.writeShort(0); // fields
        out.writeShort(2); // methods
        writeMethod(out, nullName, signature, code, nullConstant);
        writeMethod(out, objectName, signature, code, objectConstant);
        out.writeShort(1); // class attributes
        out.writeShort(bootstrapAttribute);
        out.writeInt(6);
        out.writeShort(1); // bootstrap methods
        out.writeShort(bootstrapHandle);
        out.writeShort(0); // bootstrap arguments
        return bytes.toByteArray();
    }

    private static void writeMethod(DataOutputStream out, int name, int signature,
                                    int code, int constant) throws IOException {
        out.writeShort(0x0009); // ACC_PUBLIC | ACC_STATIC
        out.writeShort(name);
        out.writeShort(signature);
        out.writeShort(1); // method attributes
        out.writeShort(code);
        out.writeInt(16); // Code attribute: 12 fixed bytes + 4 code bytes
        out.writeShort(1); // max_stack
        out.writeShort(0); // max_locals
        out.writeInt(4);
        out.writeByte(0x13); // ldc_w
        out.writeShort(constant);
        out.writeByte(0xb0); // areturn
        out.writeShort(0); // exception table
        out.writeShort(0); // nested attributes
    }

    private static final class Pool {
        final ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        final DataOutputStream out = new DataOutputStream(bytes);
        int count = 1;

        int utf8(String text) throws IOException {
            int index = count++;
            out.writeByte(1);
            out.writeUTF(text);
            return index;
        }

        int clazz(String name) throws IOException {
            int utf = utf8(name);
            int index = count++;
            out.writeByte(7);
            out.writeShort(utf);
            return index;
        }

        int pair(int tag, int first, int second) throws IOException {
            int index = count++;
            out.writeByte(tag);
            out.writeShort(first);
            out.writeShort(second);
            return index;
        }

        int handle(int kind, int reference) throws IOException {
            int index = count++;
            out.writeByte(15);
            out.writeByte(kind);
            out.writeShort(reference);
            return index;
        }
    }

    public static void main(String[] args) throws Throwable {
        Class<?> generated = MethodHandles.lookup().defineClass(generateClass());
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
