package com.yolov8.security.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.yolov8.security.config.AppConfig;
import com.yolov8.security.model.DetectionData;
import com.yolov8.security.model.StatsResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Service
public class DetectionService {

    private static final Logger log = LoggerFactory.getLogger(DetectionService.class);
    /** One directory walk serves both JSON detections and frame_*.jpg listing. */
    private record DirScan(List<DetectionData> detections, List<String> imageFiles, int totalDetectionCount) {}

    private static final int MAX_DETECTIONS_IN_STATS_PAYLOAD = 200;

    private final AppConfig appConfig;
    private final ObjectMapper objectMapper;

    private DirScan scanCache;
    private long scanCacheTimeMs;
    private static final long SCAN_CACHE_TTL_MS = 2000L;

    public DetectionService(AppConfig appConfig, ObjectMapper objectMapper) {
        this.appConfig = appConfig;
        this.objectMapper = objectMapper;
    }

    /** Call after bulk deletes so the next read sees an empty / updated folder. */
    public void invalidateScanCache() {
        scanCache = null;
        scanCacheTimeMs = 0L;
    }

    private DirScan getOrScanUploadDir() throws IOException {
        long now = System.currentTimeMillis();
        if (scanCache != null && (now - scanCacheTimeMs) < SCAN_CACHE_TTL_MS) {
            return scanCache;
        }
        DirScan fresh = scanUploadDirectory();
        scanCache = fresh;
        scanCacheTimeMs = now;
        return fresh;
    }

    /**
     * Single {@link Files#walk} collects detection JSON and image filenames (sorted newest first).
     */
    private DirScan scanUploadDirectory() throws IOException {
        File dataDir = new File(appConfig.getFile().getUploadDir());
        if (!dataDir.exists()) {
            log.warn("Data directory does not exist: {}", dataDir.getAbsolutePath());
            return new DirScan(Collections.emptyList(), Collections.emptyList(), 0);
        }

        List<Path> jsonPaths = new ArrayList<>();
        List<Path> jpgPaths = new ArrayList<>();

        try (Stream<Path> paths = Files.walk(dataDir.toPath())) {
            paths.filter(Files::isRegularFile).forEach(p -> {
                String name = p.getFileName().toString();
                if (name.startsWith("detection_") && name.endsWith(".json")) {
                    jsonPaths.add(p);
                } else if (name.startsWith("frame_") && name.endsWith(".jpg")) {
                    jpgPaths.add(p);
                }
            });
        }

        Comparator<Path> byMtimeDesc = (a, b) -> {
            try {
                return Long.compare(Files.getLastModifiedTime(b).toMillis(),
                        Files.getLastModifiedTime(a).toMillis());
            } catch (IOException e) {
                return 0;
            }
        };
        jsonPaths.sort(byMtimeDesc);
        jpgPaths.sort(byMtimeDesc);

        int totalCount = jsonPaths.size();

        // Only parse the most recent MAX_DETECTIONS_IN_STATS_PAYLOAD files for performance
        List<DetectionData> detections = jsonPaths.stream()
                .limit(MAX_DETECTIONS_IN_STATS_PAYLOAD)
                .map(this::loadDetectionFile)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());

        List<String> images = jpgPaths.stream()
                .map(p -> p.getFileName().toString())
                .collect(Collectors.toList());

        log.info("Scanned {}: {} JSON files (parsed {}), {} JPG files",
                dataDir.getAbsolutePath(), totalCount, detections.size(), images.size());

        return new DirScan(detections, images, totalCount);
    }

    /**
     * Lightweight summary: counts only, no detection list. For frequent polling.
     */
    public Map<String, Object> getStatsSummary() {
        try {
            DirScan scan = getOrScanUploadDir();
            List<DetectionData> allDetections = scan.detections();
            StatsResponse.BehaviorCounts bc = calculateBehaviorCounts(allDetections);

            Map<String, Object> summary = new LinkedHashMap<>();
            summary.put("totalDetections", scan.totalDetectionCount());
            summary.put("totalImages", scan.imageFiles().size());

            Map<String, Integer> counts = new LinkedHashMap<>();
            counts.put("跌倒", bc.getFall());
            counts.put("打架", bc.getFight());
            counts.put("离岗", bc.getAbsent());
            counts.put("疲劳", bc.getFatigue());
            counts.put("人员聚集", bc.getGather());
            summary.put("behaviorCounts", counts);

            return summary;
        } catch (Exception e) {
            log.error("Error getting stats summary", e);
            return Map.of("totalDetections", 0, "totalImages", 0, "behaviorCounts", Map.of());
        }
    }

    public StatsResponse getStats() {
        try {
            DirScan scan = getOrScanUploadDir();
            List<DetectionData> allDetections = scan.detections();
            List<String> imageFiles = scan.imageFiles();

            StatsResponse.BehaviorCounts behaviorCounts = calculateBehaviorCounts(allDetections);

            StatsResponse stats = new StatsResponse();
            stats.setTotalDetections(scan.totalDetectionCount());
            stats.setTotalImages(imageFiles.size());
            stats.setBehaviorCounts(behaviorCounts);
            stats.setAllDetections(allDetections);
            stats.setRecentDetections(allDetections.stream()
                    .limit(50)
                    .collect(Collectors.toList()));

            return stats;
        } catch (Exception e) {
            log.error("Error getting stats", e);
            return new StatsResponse();
        }
    }

    private StatsResponse.BehaviorCounts calculateBehaviorCounts(List<DetectionData> detections) {
        StatsResponse.BehaviorCounts behaviorCounts = new StatsResponse.BehaviorCounts();

        for (DetectionData detection : detections) {
            if (detection.getActions() != null) {
                for (String action : detection.getActions()) {
                    switch (action) {
                        case "跌倒": behaviorCounts.setFall(behaviorCounts.getFall() + 1); break;
                        case "打架": behaviorCounts.setFight(behaviorCounts.getFight() + 1); break;
                        case "离岗": behaviorCounts.setAbsent(behaviorCounts.getAbsent() + 1); break;
                        case "疲劳": behaviorCounts.setFatigue(behaviorCounts.getFatigue() + 1); break;
                        case "人员聚集": behaviorCounts.setGather(behaviorCounts.getGather() + 1); break;
                    }
                }
            }
        }
        return behaviorCounts;
    }

    public List<DetectionData> getDetections() {
        try {
            return getOrScanUploadDir().detections();
        } catch (Exception e) {
            log.error("Error getting detections", e);
            return Collections.emptyList();
        }
    }

    public List<String> getRecentFrames() {
        try {
            return getOrScanUploadDir().imageFiles().stream()
                    .limit(appConfig.getMonitor().getMaxRecentFrames())
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("Error getting recent frames", e);
            return Collections.emptyList();
        }
    }

    public List<String> getAllFrames() {
        try {
            return new ArrayList<>(getOrScanUploadDir().imageFiles());
        } catch (Exception e) {
            log.error("Error getting all frames", e);
            return Collections.emptyList();
        }
    }

    public Map<String, Object> getAllImages() {
        try {
            List<String> images = getOrScanUploadDir().imageFiles();
            Map<String, Object> result = new HashMap<>();
            result.put("status", "success");
            result.put("images", images);
            return result;
        } catch (Exception e) {
            log.error("Error getting all images", e);
            Map<String, Object> result = new HashMap<>();
            result.put("status", "error");
            result.put("message", e.getMessage());
            return result;
        }
    }

    public Map<String, Object> deleteAllImages() {
        try {
            File dataDir = new File(appConfig.getFile().getUploadDir());
            if (dataDir.exists() && dataDir.isDirectory()) {
                File[] files = dataDir.listFiles((dir, name) ->
                        name.startsWith("frame_") && name.endsWith(".jpg") ||
                                name.startsWith("detection_") && name.endsWith(".json")
                );

                if (files != null) {
                    for (File file : files) {
                        file.delete();
                    }
                }
            }

            invalidateScanCache();

            Map<String, Object> result = new HashMap<>();
            result.put("status", "success");
            result.put("message", "所有图片和检测记录已删除");
            return result;
        } catch (Exception e) {
            log.error("Error deleting images", e);
            Map<String, Object> result = new HashMap<>();
            result.put("status", "error");
            result.put("message", e.getMessage());
            return result;
        }
    }

    public Map<String, Object> getMonitorStatus() {
        try {
            Map<String, Object> result = new HashMap<>();
            result.put("status", "online");
            result.put("message", "监控正常运行");
            SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss");
            result.put("update_time", sdf.format(new Date()));
            return result;
        } catch (Exception e) {
            log.error("Error getting monitor status", e);
            Map<String, Object> result = new HashMap<>();
            result.put("status", "error");
            result.put("message", e.getMessage());
            return result;
        }
    }

    public Map<String, Object> openFolder(String folderType) {
        try {
            String folderPath;
            switch (folderType) {
                case "screenshots":
                    folderPath = appConfig.getFile().getUploadDir();
                    break;
                case "videos":
                    folderPath = appConfig.getFile().getResultDir();
                    break;
                default:
                    Map<String, Object> result = new HashMap<>();
                    result.put("status", "error");
                    result.put("message", "Invalid folder type");
                    return result;
            }

            File folder = new File(folderPath);
            if (!folder.exists()) {
                folder.mkdirs();
            }

            java.awt.Desktop.getDesktop().open(folder);

            Map<String, Object> result = new HashMap<>();
            result.put("status", "success");
            result.put("message", "Opened " + folderPath);
            return result;
        } catch (Exception e) {
            log.error("Error opening folder", e);
            Map<String, Object> result = new HashMap<>();
            result.put("status", "error");
            result.put("message", e.getMessage());
            return result;
        }
    }

    private DetectionData loadDetectionFile(Path path) {
        try {
            // 使用UTF-8编码读取JSON文件
            return objectMapper.readValue(Files.newBufferedReader(path, StandardCharsets.UTF_8), DetectionData.class);
        } catch (IOException e) {
            log.error("Error loading detection file: {}", path, e);
            return null;
        }
    }

    public Map<String, Object> getSystemInfo() {
        Map<String, Object> info = new HashMap<>();
        try {
            File dataDir = new File(appConfig.getFile().getUploadDir());
            long totalSize = 0;
            int jsonCount = 0;
            int jpgCount = 0;
            if (dataDir.exists() && dataDir.isDirectory()) {
                File[] files = dataDir.listFiles();
                if (files != null) {
                    for (File f : files) {
                        if (f.isFile()) {
                            totalSize += f.length();
                            String name = f.getName();
                            if (name.startsWith("detection_") && name.endsWith(".json")) jsonCount++;
                            else if (name.startsWith("frame_") && name.endsWith(".jpg")) jpgCount++;
                        }
                    }
                }
            }
            Runtime rt = Runtime.getRuntime();
            long usedMemory = (rt.totalMemory() - rt.freeMemory()) / (1024 * 1024);
            long maxMemory = rt.maxMemory() / (1024 * 1024);

            info.put("status", "success");
            info.put("dataDirSizeMb", Math.round(totalSize / 1024.0 / 1024.0 * 100.0) / 100.0);
            info.put("detectionCount", jsonCount);
            info.put("imageCount", jpgCount);
            info.put("jvmUsedMb", usedMemory);
            info.put("jvmMaxMb", maxMemory);
        } catch (Exception e) {
            log.error("Error getting system info", e);
            info.put("status", "error");
            info.put("message", e.getMessage());
        }
        return info;
    }
}
