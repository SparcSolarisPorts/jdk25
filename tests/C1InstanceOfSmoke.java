public class C1InstanceOfSmoke {
    interface Tag {}
    static class Base {}
    static class Child extends Base implements Tag {}
    static volatile int matches;

    static boolean test(Class<?> type, Object value) {
        return type.isInstance(value);
    }

    public static void main(String[] args) {
        Class<?>[] types = {Child.class, Base.class, Tag.class, String.class,
            Object.class, int.class, void.class, Object[].class, String[].class,
            int[].class, Cloneable.class, java.io.Serializable.class};
        Object[] values = {new Child(), new Base(), "text", null,
            new String[]{"a"}, new Object[1], new int[1]};
        boolean[][] expected = {
            {true,false,false,false,false,false,false},
            {true,true,false,false,false,false,false},
            {true,false,false,false,false,false,false},
            {false,false,true,false,false,false,false},
            {true,true,true,false,true,true,true},
            {false,false,false,false,false,false,false},
            {false,false,false,false,false,false,false},
            {false,false,false,false,true,true,false},
            {false,false,false,false,true,false,false},
            {false,false,false,false,false,false,true},
            {false,false,false,false,true,true,true},
            {false,false,true,false,true,true,true}
        };
        for (int round = 0; round < 20000; round++) {
            for (int i = 0; i < types.length; i++) {
                for (int j = 0; j < values.length; j++) {
                    boolean result = test(types[i], values[j]);
                    if (result != expected[i][j])
                        throw new AssertionError(types[i] + " / value index " + j);
                    if (result) matches++;
                }
            }
        }
        try {
            test(null, new Object());
            throw new AssertionError("null Class should throw NPE");
        } catch (NullPointerException expectedException) {}
        System.out.println("PASS: Class.isInstance classes, interfaces, arrays, primitives and nulls");
    }
}
