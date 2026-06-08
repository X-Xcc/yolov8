package com.yolov8.security.controller;

import com.yolov8.security.config.AppConfig;
import com.yolov8.security.service.CameraConfigService;
import com.yolov8.security.service.DemoService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import jakarta.servlet.http.HttpServletResponse;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import javax.imageio.ImageIO;

@RestController
public class VideoStreamController {

    private static final Logger log = LoggerFactory.getLogger(VideoStreamController.class);

    @Value("${app.video.stream-poll-interval-ms:16}")
    private int streamPollIntervalMs;

    @Value("${app.video.no-frame-poll-interval-ms:200}")
    private int noFramePollIntervalMs;

    @Value("${app.video.frame-ttl-ms:30000}")
    private long frameTtlMs;

    private static final long TEST_FRAME_CACHE_MS = 5000L; // 5s cache, avoid flicker

    // Test frame cache per camera
    private final Map<String, BufferedImage> cachedTestFrames = new ConcurrentHashMap<>();
    private final Map<String, Long> cachedTestFrameAtMs = new ConcurrentHashMap<>();

    // ConcurrentHashMap<camId, jpegBytes>，每个摄像头独立存储最新帧
    /** Multi-camera frame storage: camId -> latest frame bytes (JPEG) */
    private static final int MAX_FRAME_ENTRIES = 32;
    private final Map<String, byte[]> latestFrameBytes = new ConcurrentHashMap<>();
    private final Map<String, Long> lastFrameIds = new ConcurrentHashMap<>();

    /** Default camera ID */
    private static final String DEFAULT_CAM = "0";

    private final AppConfig appConfig;
    private final DemoService demoService;
    private final CameraConfigService cameraConfigService;

    public VideoStreamController(AppConfig appConfig, DemoService demoService, CameraConfigService cameraConfigService) {
        this.appConfig = appConfig;
        this.demoService = demoService;
        this.cameraConfigService = cameraConfigService;
    }

    // Python POST进来，MJPEG读出去
    /**
     * Update frame bytes for a specific camera.
     * The incoming Python payload is already JPEG, so keep it as-is to avoid extra decode/re-encode work.
     */
    public void updateFrame(byte[] frameBytes, String camId) {
        String id = (camId != null && !camId.isEmpty()) ? camId : DEFAULT_CAM;
        if (frameBytes == null || frameBytes.length == 0) {
            return;
        }
        // OOM 防护：限制最大条目数，移除最旧的条目
        if (latestFrameBytes.size() >= MAX_FRAME_ENTRIES && !latestFrameBytes.containsKey(id)) {
            String oldest = null;
            long oldestTs = Long.MAX_VALUE;
            for (Map.Entry<String, Long> e : lastFrameIds.entrySet()) {
                if (e.getValue() < oldestTs) {
                    oldestTs = e.getValue();
                    oldest = e.getKey();
                }
            }
            if (oldest != null) {
                latestFrameBytes.remove(oldest);
                lastFrameIds.remove(oldest);
            }
        }
        latestFrameBytes.put(id, frameBytes);
        lastFrameIds.put(id, System.currentTimeMillis());
    }

    /**
     * Update frame for a specific camera. Converts to JPEG bytes immediately.
     */
    public void updateFrame(BufferedImage frame, String camId) {
        String id = (camId != null && !camId.isEmpty()) ? camId : DEFAULT_CAM;
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ImageIO.write(frame, "jpg", baos);
            updateFrame(baos.toByteArray(), id);
        } catch (IOException e) {
            log.error("Error encoding frame for cam={}", id, e);
        }
    }

    /**
     * Update frame with person count (used by StatsController).
     */
    public void updateFrame(BufferedImage frame, String camId, int personCount) {
        updateFrame(frame, camId);
    }

    /**
     * Legacy single-camera update (backward compatible).
     */
    public void updateFrame(BufferedImage frame) {
        updateFrame(frame, DEFAULT_CAM);
    }

    // ┌──────────────────────────────────────────────┐
    // │  摄像头 HTTP MJPEG 代理 — 绕过浏览器嵌入式凭证限制 │
    // └──────────────────────────────────────────────┘
    /**
     * Proxy camera MJPEG stream. Maps /proxy/cam-N/ to camera's HTTP MJPEG URL.
     */
    @GetMapping(value = "/proxy/{camId}/")
    public void proxyCameraMjpeg(@PathVariable String camId, HttpServletResponse response) {
        // 从 cameras.json 读取目标 URL
        String targetUrl = null;
        String username = null;
        String password = null;
        try {
            var cameras = cameraConfigService.getAllCameras();
            for (var cam : cameras) {
                if (camId.equals(cam.getId())) {
                    targetUrl = cam.getHttpMjpegUrl();
                    username = cam.getUsername();
                    password = cam.getPassword();
                    break;
                }
            }
        } catch (Exception e) {
            log.warn("读取摄像头配置失败: {}", e.getMessage());
        }

        if (targetUrl == null || targetUrl.isEmpty()) {
            response.setStatus(404);
            return;
        }

        try {
            java.net.URL url = new java.net.URL(targetUrl);
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(0); // 无限读取
            conn.setRequestProperty("Accept", "multipart/x-mixed-replace, image/jpeg, */*");

            // Basic auth
            if (username != null && !username.isEmpty() && password != null && !password.isEmpty()) {
                String auth = username + ":" + password;
                conn.setRequestProperty("Authorization",
                    "Basic " + java.util.Base64.getEncoder().encodeToString(auth.getBytes()));
            }

            int status = conn.getResponseCode();
            if (status >= 200 && status < 400) {
                response.setContentType(conn.getContentType() != null ? conn.getContentType() : "multipart/x-mixed-replace;boundary=frame");
                response.setHeader("Cache-Control", "no-cache");
                response.setHeader("Connection", "keep-alive");

                try (java.io.InputStream in = conn.getInputStream();
                     java.io.OutputStream out = response.getOutputStream()) {
                    byte[] buf = new byte[8192];
                    int n;
                    while ((n = in.read(buf)) != -1) {
                        out.write(buf, 0, n);
                        out.flush();
                    }
                }
            } else {
                response.setStatus(502);
                log.warn("摄像头代理返回 HTTP {}: {}", status, targetUrl);
            }
            conn.disconnect();
        } catch (java.io.IOException e) {
            log.debug("摄像头代理断开: {} - {}", camId, e.getMessage());
        }
    }

    // MJPEG流
    /**
     * MJPEG video feed endpoint. Supports ?cam=0, ?cam=1, etc.
     */
    @GetMapping(value = "/video_feed")
    public void getVideoFeed(@RequestParam(required = false, defaultValue = DEFAULT_CAM) String cam,
                             HttpServletResponse response) {
        response.setContentType("multipart/x-mixed-replace;boundary=frame");
        response.setHeader("Cache-Control", "no-cache");
        response.setHeader("Connection", "keep-alive");
        response.setHeader("Pragma", "no-cache");

        try (OutputStream out = response.getOutputStream()) {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    byte[] frameBytes = getFrameBytes(cam);
                    if (frameBytes != null && frameBytes.length > 0) {
                        writeFrame(out, frameBytes);
                        Thread.sleep(streamPollIntervalMs);
                    } else {
                        byte[] testFrame = getTestFrameBytes(cam);
                        if (testFrame.length > 0) {
                            writeFrame(out, testFrame);
                        }
                        Thread.sleep(noFramePollIntervalMs);
                    }
                } catch (IOException e) {
                    log.debug("Client disconnected during frame write (cam={})", cam);
                    break;
                }
            }
        } catch (IOException e) {
            log.debug("Client disconnected (cam={})", cam);
        } catch (InterruptedException e) {
            log.debug("Video feed interrupted (cam={})", cam);
            Thread.currentThread().interrupt();
        }
    }

    /**
     * Get list of active cameras (for API).
     * Returns both cameras with live frames AND configured cameras (so frontend can display them).
     */
    @GetMapping(value = "/api/cameras", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getCameras() {
        // Merge live frame cameras with configured cameras
        java.util.Set<String> allCameraIds = new java.util.LinkedHashSet<>(latestFrameBytes.keySet());
        try {
            cameraConfigService.getAllCameras().forEach(cam -> allCameraIds.add(cam.getId()));
        } catch (Exception e) {
            log.debug("Failed to load camera config: {}", e.getMessage());
        }
        Map<String, Object> result = new java.util.LinkedHashMap<>();
        result.put("status", "success");
        result.put("cameras", allCameraIds);
        result.put("count", allCameraIds.size());
        return result;
    }

    /** Camera stats for SSE broadcasting */
    public Map<String, Object> getCameraStats() {
        // Demo mode: return virtual camera stats
        if (appConfig != null && appConfig.isDemoMode() && demoService != null) {
            Map<String, Object> stats = new java.util.LinkedHashMap<>();
            java.util.List<Map<String, Object>> camList = new java.util.ArrayList<>();
            java.util.Random rand = new java.util.Random();
            for (String[] def : DemoService.CAMERA_DEFS) {
                Map<String, Object> info = new java.util.LinkedHashMap<>();
                info.put("id", def[0]);
                info.put("name", def[1]);
                boolean online = rand.nextDouble() > 0.2;
                info.put("online", online);
                info.put("personCount", online ? rand.nextInt(5) + 1 : 0);
                camList.add(info);
            }
            stats.put("cameras", camList);
            stats.put("activeCount", DemoService.CAMERA_DEFS.length);
            return stats;
        }

        Map<String, Object> stats = new java.util.LinkedHashMap<>();
        long now = System.currentTimeMillis();
        java.util.List<Map<String, Object>> camList = new java.util.ArrayList<>();
        for (Map.Entry<String, byte[]> entry : latestFrameBytes.entrySet()) {
            Map<String, Object> info = new java.util.LinkedHashMap<>();
            info.put("id", entry.getKey());
            Long ts = lastFrameIds.get(entry.getKey());
            info.put("online", ts != null && (now - ts) < frameTtlMs);
            camList.add(info);
        }
        stats.put("cameras", camList);
        stats.put("activeCount", latestFrameBytes.size());
        return stats;
    }

    private byte[] getFrameBytes(String cam) {
        // Check TTL — expire stale frames
        Long ts = lastFrameIds.get(cam);
        if (ts != null && System.currentTimeMillis() - ts > frameTtlMs) {
            latestFrameBytes.remove(cam);
            lastFrameIds.remove(cam);
            return null;
        }
        return latestFrameBytes.get(cam);
    }

    // 无真实帧时生成模拟帧（灰色+文字），用于前端占位显示
    private byte[] getTestFrameBytes(String cam) {
        BufferedImage testFrame = getOrCreateCachedTestFrame(cam);
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ImageIO.write(testFrame, "jpg", baos);
            return baos.toByteArray();
        } catch (IOException e) {
            return new byte[0];
        }
    }

    private BufferedImage getOrCreateCachedTestFrame(String cam) {
        long now = System.currentTimeMillis();
        BufferedImage cached = cachedTestFrames.get(cam);
        Long cachedAt = cachedTestFrameAtMs.get(cam);
        if (cached != null && cachedAt != null && (now - cachedAt) < TEST_FRAME_CACHE_MS) {
            return cached;
        }
        BufferedImage fresh = generateTestFrame(cam);
        cachedTestFrames.put(cam, fresh);
        cachedTestFrameAtMs.put(cam, now);
        return fresh;
    }

    private BufferedImage generateTestFrame(String cam) {
        int width = 1280;
        int height = 720;
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = image.createGraphics();

        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        // Background
        g2d.setColor(new Color(12, 18, 32));
        g2d.fillRect(0, 0, width, height);

        // Grid
        g2d.setColor(new Color(40, 60, 100));
        for (int i = 0; i < width; i += 50) g2d.drawLine(i, 0, i, height);
        for (int i = 0; i < height; i += 50) g2d.drawLine(0, i, width, i);

        // Camera label centered
        g2d.setColor(new Color(0, 0, 0, 150));
        g2d.fillRect(0, height / 2 - 40, width, 80);

        g2d.setColor(new Color(160, 180, 200));
        g2d.setFont(new Font("Microsoft YaHei", Font.BOLD, 24));
        String label = "等待视频信号 - " + getCameraLabel(cam);
        FontMetrics fm = g2d.getFontMetrics();
        g2d.drawString(label, (width - fm.stringWidth(label)) / 2, height / 2 + 8);

        g2d.dispose();
        return image;
    }

    private String getCameraLabel(String cam) {
        switch (cam) {
            case "0": return "A区-主监控";
            case "1": return "B区-走廊";
            case "2": return "C区-操场";
            default: return "摄像头 " + cam;
        }
    }

    // 写--frame\r\n + Content-Type + JPEG二进制，组成MJPEG multipart协议
    private void writeFrame(OutputStream out, byte[] frameBytes) throws IOException {
        out.write(("--frame\r\n").getBytes());
        out.write(("Content-Type: image/jpeg\r\n").getBytes());
        out.write(("Content-Length: " + frameBytes.length + "\r\n").getBytes());
        out.write(("\r\n").getBytes());
        out.write(frameBytes);
        out.write(("\r\n").getBytes());
        out.flush();
    }
}
