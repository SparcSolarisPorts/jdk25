import java.lang.foreign.*;
import java.lang.invoke.*;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicInteger;
import static java.lang.foreign.ValueLayout.*;

public class PanamaNativeSmoke {
    static Linker linker;
    static SymbolLookup lookup;
    static Arena callbackArena;
    static MethodHandle callbackDowncall;
    static final AtomicInteger calls = new AtomicInteger();
    static final StructLayout PAIR = MemoryLayout.structLayout(JAVA_DOUBLE, JAVA_INT, MemoryLayout.paddingLayout(4));
    static final StructLayout BIG = MemoryLayout.structLayout(MemoryLayout.sequenceLayout(5, JAVA_LONG));
    static int checks;
    static void check(boolean ok, String label) {
        if (!ok) throw new AssertionError(label);
        checks++;
    }
    static Object call(String name, FunctionDescriptor fd, Object... args) throws Throwable {
        return linker.downcallHandle(lookup.findOrThrow(name), fd).invokeWithArguments(args);
    }
    static MethodHandle target(String name, Class<?> ret, Class<?>... args) throws Exception {
        return MethodHandles.lookup().findStatic(PanamaNativeSmoke.class,name,MethodType.methodType(ret,args));
    }
    public static int callback(int x) {
        calls.incrementAndGet();
        // Re-enter native code from Java, on both Java and attached C threads.
        try { return (int) callbackDowncall.invokeExact(x*3-1); }
        catch (Throwable t) { throw new AssertionError(t); }
    }
    public static byte callbackByte(byte x) { return (byte)(x ^ 0x5a); }
    public static MemorySegment callbackPair(MemorySegment p) {
        MemorySegment r=callbackArena.allocate(PAIR);
        r.set(JAVA_DOUBLE,0,p.get(JAVA_DOUBLE,0)+0.5);
        r.set(JAVA_INT,8,p.get(JAVA_INT,8)-3);
        return r;
    }
    public static void main(String[] args) throws Throwable {
        linker=Linker.nativeLinker();
        System.out.println("Linker implementation: "+linker.getClass().getName());
        if (Boolean.getBoolean("panama.requireFallback"))
            check(linker.getClass().getName().endsWith(".fallback.FallbackLinker"),"libffi backend selected");
        try(Arena arena=Arena.ofConfined(); Arena shared=Arena.ofShared()) {
            callbackArena=shared;
            lookup=SymbolLookup.libraryLookup(Path.of(args[0]).toAbsolutePath(),shared);
            check(linker.canonicalLayouts().get("int").byteSize()==4,"C int size");
            check(linker.canonicalLayouts().get("long").byteSize()==8,"LP64 C long size");
            check(linker.canonicalLayouts().get("void*").byteSize()==8,"LP64 pointer size");
            for(byte x:new byte[]{0,1,127,-1,-128}) {
                check((byte)call("nf_i8",FunctionDescriptor.of(JAVA_BYTE,JAVA_BYTE),x)==x,"signed byte");
                check((boolean)call("nf_u8",FunctionDescriptor.of(JAVA_BOOLEAN,JAVA_BOOLEAN),x!=0)==(x!=0),"bool");
            }
            for(short x:new short[]{0,1,32767,-1,-32768})
                check((short)call("nf_i16",FunctionDescriptor.of(JAVA_SHORT,JAVA_SHORT),x)==x,"signed short");
            for(char x:new char[]{0,1,32767,32768,65535})
                check((char)call("nf_u16",FunctionDescriptor.of(JAVA_CHAR,JAVA_CHAR),x)==x,"unsigned char16");
            for(int x:new int[]{0,1,-1,Integer.MIN_VALUE,Integer.MAX_VALUE,0x87654321})
                check((int)call("nf_i32",FunctionDescriptor.of(JAVA_INT,JAVA_INT),x)==x,"signed int");
            for(long x:new long[]{0,1,-1,Long.MIN_VALUE,Long.MAX_VALUE,0x1234567887654321L})
                check((long)call("nf_i64",FunctionDescriptor.of(JAVA_LONG,JAVA_LONG),x)==x,"long");
            check(Float.floatToRawIntBits((float)call("nf_float",FunctionDescriptor.of(JAVA_FLOAT,JAVA_FLOAT),-0.0f))==0x80000000,"float bits");
            check((double)call("nf_double",FunctionDescriptor.of(JAVA_DOUBLE,JAVA_DOUBLE),-1234.5)==-1234.5,"double");
            MemorySegment p=arena.allocate(32);
            check(((MemorySegment)call("nf_pointer",FunctionDescriptor.of(ADDRESS,ADDRESS),p)).address()==p.address(),"pointer return");
            call("nf_write",FunctionDescriptor.ofVoid(ADDRESS,JAVA_INT),p,-1234567);
            check(p.get(JAVA_INT,0)==-1234567,"void downcall");
            MemoryLayout[] longs=new MemoryLayout[10];Arrays.fill(longs,JAVA_LONG);
            check((long)call("nf_many",FunctionDescriptor.of(JAVA_LONG,longs),1L,2L,3L,4L,5L,6L,7L,8L,9L,10L)==385L,"integer register/stack arguments");
            check((double)call("nf_mixed",FunctionDescriptor.of(JAVA_DOUBLE,JAVA_LONG,JAVA_DOUBLE,JAVA_INT,JAVA_FLOAT,JAVA_LONG,JAVA_DOUBLE,JAVA_LONG,JAVA_DOUBLE,JAVA_INT,JAVA_DOUBLE),
                1L,2.0,3,4.0f,5L,6.0,7L,8.0,9,10.0)==55.0,"mixed ABI arguments");
            MemoryLayout[] doubles=new MemoryLayout[20];Arrays.fill(doubles,JAVA_DOUBLE);
            Object[] values=new Object[20];for(int i=0;i<20;i++)values[i]=(double)i;
            check((double)call("nf_fp20",FunctionDescriptor.of(JAVA_DOUBLE,doubles),values)==190.0,"floating register/stack arguments");
            MemorySegment pair=arena.allocate(PAIR);pair.set(JAVA_DOUBLE,0,1.25);pair.set(JAVA_INT,8,-10);
            MemorySegment pairOut=(MemorySegment)call("nf_pair",FunctionDescriptor.of(PAIR,PAIR,JAVA_DOUBLE,JAVA_INT),arena,pair,2.5,7);
            check(pairOut.get(JAVA_DOUBLE,0)==3.75&&pairOut.get(JAVA_INT,8)==-3,"mixed small struct argument/return");
            MemorySegment big=arena.allocate(BIG);for(int i=0;i<5;i++)big.setAtIndex(JAVA_LONG,i,100L+i);
            MemorySegment bigOut=(MemorySegment)call("nf_big",FunctionDescriptor.of(BIG,BIG,JAVA_LONG),arena,big,20L);
            for(int i=0;i<5;i++)check(bigOut.getAtIndex(JAVA_LONG,i)==120L+2*i,"large struct hidden return buffer");
            MethodHandle variadic=linker.downcallHandle(lookup.findOrThrow("nf_variadic"),
                FunctionDescriptor.of(JAVA_DOUBLE,JAVA_INT,JAVA_INT,JAVA_DOUBLE,JAVA_INT,JAVA_DOUBLE,JAVA_INT,JAVA_DOUBLE),Linker.Option.firstVariadicArg(1));
            check((double)variadic.invokeExact(3,1,1.5,2,2.5,3,3.5)==13.5,"variadic integer/floating arguments");
            MemorySegment state=arena.allocate(Linker.Option.captureStateLayout());
            MethodHandle withErrno=linker.downcallHandle(lookup.findOrThrow("nf_errno"),FunctionDescriptor.of(JAVA_INT),Linker.Option.captureCallState("errno"));
            check((int)withErrno.invokeExact(state)==-7,"errno function return");
            long errnoOffset=Linker.Option.captureStateLayout().byteOffset(MemoryLayout.PathElement.groupElement("errno"));
            check(state.get(JAVA_INT,errnoOffset)==(int)call("nf_edom",FunctionDescriptor.of(JAVA_INT)),"captured errno");
            byte[] bytes=new byte[12];Arrays.fill(bytes,(byte)0x55);
            MethodHandle heap=linker.downcallHandle(lookup.findOrThrow("nf_heap"),FunctionDescriptor.of(JAVA_INT,ADDRESS,JAVA_INT),Linker.Option.critical(true));
            check((int)heap.invokeExact(MemorySegment.ofArray(bytes).asSlice(3,5),5)==5,"critical heap return");
            for(int i=0;i<12;i++)check(bytes[i]==(byte)(i>=3&&i<8?0xa0+i-3:0x55),"nonzero heap offset/guards");
            callbackDowncall=linker.downcallHandle(lookup.findOrThrow("nf_i32"),FunctionDescriptor.of(JAVA_INT,JAVA_INT));
            MemorySegment cb=linker.upcallStub(target("callback",int.class,int.class),FunctionDescriptor.of(JAVA_INT,JAVA_INT),shared);
            int expected=3*19*20/2-20;
            for(int i=0;i<3;i++) {
                check((int)call("nf_callback",FunctionDescriptor.of(JAVA_INT,ADDRESS,JAVA_INT),cb,20)==expected,"reentrant Java-thread callback");
                check((int)call("nf_pthread_callback",FunctionDescriptor.of(JAVA_INT,ADDRESS,JAVA_INT),cb,20)==expected,"attached pthread callback");
            }
            check(calls.get()==120,"all callbacks completed");
            MemorySegment cbByte=linker.upcallStub(target("callbackByte",byte.class,byte.class),FunctionDescriptor.of(JAVA_BYTE,JAVA_BYTE),shared);
            check((byte)call("nf_callback_i8",FunctionDescriptor.of(JAVA_BYTE,ADDRESS,JAVA_BYTE),cbByte,(byte)-101)==(byte)(-101^0x5a),"narrow callback return");
            MemorySegment cbPair=linker.upcallStub(target("callbackPair",MemorySegment.class,MemorySegment.class),FunctionDescriptor.of(PAIR,PAIR),shared);
            MemorySegment cbPairOut=(MemorySegment)call("nf_callback_pair",FunctionDescriptor.of(PAIR,ADDRESS,PAIR),arena,cbPair,pair);
            check(cbPairOut.get(JAVA_DOUBLE,0)==1.75&&cbPairOut.get(JAVA_INT,8)==-13,"struct callback return");
            SymbolLookup system=linker.defaultLookup();
            MethodHandle strlen=linker.downcallHandle(system.findOrThrow("strlen"),FunctionDescriptor.of(JAVA_LONG,ADDRESS));
            check((long)strlen.invokeExact(arena.allocateFrom("Solaris Panama"))==14L,"default libc lookup");
            MethodHandle cos=linker.downcallHandle(system.findOrThrow("cos"),FunctionDescriptor.of(JAVA_DOUBLE,JAVA_DOUBLE));
            check((double)cos.invokeExact(0.0)==1.0,"default libm lookup");
        }
        System.out.println("PASS: Panama native linker, "+checks+" ABI/memory/callback checks");
    }
}
