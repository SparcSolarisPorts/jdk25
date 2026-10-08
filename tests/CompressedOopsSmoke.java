public class CompressedOopsSmoke {
    static final Object anchor = new Object();
    static final Cell[] roots = new Cell[1024];
    static class Cell {
        final long stamp;
        final Object owner;
        final byte[] bytes;
        Cell(long stamp) {
            this.stamp = stamp;
            this.owner = anchor;
            this.bytes = new byte[97];
            bytes[0] = (byte) stamp;
            bytes[96] = (byte) (stamp >>> 8);
        }
    }
    static void check(Cell cell, long stamp) {
        if (cell == null || cell.owner != anchor || cell.stamp != stamp
                || cell.bytes[0] != (byte) stamp
                || cell.bytes[96] != (byte) (stamp >>> 8)) {
            throw new AssertionError("Corrupt compressed reference or payload: " + stamp);
        }
    }
    public static void main(String[] args) {
        for (int round = 0; round < 128; round++) {
            for (int i = 0; i < roots.length; i++) {
                long stamp = (long) round * roots.length + i;
                roots[i] = new Cell(stamp);
                check(roots[i], stamp);
            }
            if ((round & 7) == 7) System.gc();
            for (int i = 0; i < roots.length; i++)
                check(roots[i], (long) round * roots.length + i);
        }
        roots[0] = null;
        if (roots[0] != null) throw new AssertionError("Null reference changed");
        System.out.println("PASS: compressed references, identity, payloads and GC");
    }
}
