import java.awt.AlphaComposite;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.Path2D;
import java.awt.image.BufferedImage;
import java.util.zip.CRC32;
import java.nio.file.Files;
import java.nio.file.Path;

/** Headless AA stroke/fill workload; compare pixel CRCs between VM modes. */
public final class MarlinOsrSmoke {
    private static final int W = 1024, H = 768;
    private static Path2D.Double path(int shape, int frame) {
        Path2D.Double p = new Path2D.Double(
                (shape & 1) == 0 ? Path2D.WIND_NON_ZERO : Path2D.WIND_EVEN_ODD);
        int seed = shape * 101 + frame * 17;
        p.moveTo(20 + (seed & 63), 20 + (seed & 127));
        for (int k = 0; k < 64; k++) {
            int a = seed + k * 73;
            double x = 12.25 + ((a * 29) & 1023);
            double y = 8.125 + ((a * 53) & 767);
            if ((k & 7) == 0) {
                p.curveTo(x - 25.375, y + 17.625,
                          x + 31.125, y - 23.25, x, y);
            } else {
                p.lineTo(x, y);
            }
        }
        p.closePath();
        return p;
    }
    private static long render(int frame) {
        BufferedImage image = new BufferedImage(W, H, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = image.createGraphics();
        try {
            g.setComposite(AlphaComposite.Src);
            g.setColor(new Color(0x182736));
            g.fillRect(0, 0, W, H);
            g.setComposite(AlphaComposite.SrcOver);
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
            for (int shape = 0; shape < 6; shape++) {
                g.setColor(new Color((shape * 0x123457 + frame * 0x234561) & 0xffffff));
                g.setStroke(new BasicStroke(0.75f + (shape % 5) * 0.5f,
                        BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                Path2D.Double p = path(shape, frame);
                if ((shape & 3) == 0) g.fill(p);
                else g.draw(p);
            }
        } finally {
            g.dispose();
        }
        CRC32 crc = new CRC32();
        for (int y = 0; y < H; y++) {
            for (int x = 0; x < W; x++) {
                int pixel = image.getRGB(x, y);
                crc.update(pixel >>> 24);
                crc.update(pixel >>> 16);
                crc.update(pixel >>> 8);
                crc.update(pixel);
            }
        }
        return crc.getValue();
    }
    public static void main(String[] args) throws Exception {
        int rounds = args.length == 0 ? 4 : Integer.parseInt(args[0]);
        long combined = 0;
        for (int frame = 0; frame < rounds; frame++) {
            combined = Long.rotateLeft(combined, 7) ^ render(frame);
        }
        String checksum = String.format("%016x", combined);
        String resultFile = System.getProperty("marlin.resultFile");
        if (resultFile != null) Files.writeString(Path.of(resultFile), checksum + "\n");
        System.out.printf("PASS: Marlin AA render crc=%s frames=%d%n", checksum, rounds);
    }
}
