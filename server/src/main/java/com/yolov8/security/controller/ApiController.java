package com.yolov8.security.controller;

import com.yolov8.security.model.ApiResponse;
import com.yolov8.security.service.SettingsService;
import com.yolov8.security.service.SettingsService.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.yolov8.security.controller.VideoStreamController;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ApiController {

    private static final Logger log = LoggerFactory.getLogger(ApiController.class);
    private final SettingsService settingsService;
    private final VideoStreamController videoStreamController;
    private final Path uploadDir;

    public ApiController(SettingsService settingsService, VideoStreamController videoStreamController,
                         @Value("${app.file.upload-dir:./data}") String uploadDir) {
        this.settingsService = settingsService;
        this.videoStreamController = videoStreamController;
        this.uploadDir = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    // --- Settings endpoints ---

    @GetMapping("/settings")
    public ResponseEntity<ApiResponse<SettingsService.Settings>> getSettings() {
        try {
            SettingsService.Settings settings = settingsService.getSettings();
            return ResponseEntity.ok(ApiResponse.success(settings));
        } catch (Exception e) {
            log.error("Error getting settings", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("读取设置失败: " + e.getMessage()));
        }
    }

    @PostMapping(value = "/update_frame", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<ApiResponse<Map<String, Object>>> updateFrame(
            @RequestParam("frame") MultipartFile frame,
            @RequestParam(value = "cam", required = false) String cam,
            @RequestParam(value = "person_count", required = false, defaultValue = "0") int personCount) {
        String camId = (cam == null || cam.isBlank()) ? "0" : cam.trim();
        try {
            byte[] frameBytes = frame.getBytes();
            if (frameBytes.length == 0) {
                return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                        .body(ApiResponse.error("空帧数据"));
            }
            videoStreamController.updateFrame(frameBytes, camId);
            SystemMetricsController.notifyFrameReceived();
            log.debug("Frame updated successfully: cam={}, personCount={}, bytes={}",
                    camId, personCount, frameBytes.length);
            return ResponseEntity.ok(ApiResponse.success(Map.of(
                    "status", "ok",
                    "cam", camId,
                    "person_count", personCount,
                    "bytes", frameBytes.length
            )));
        } catch (IOException e) {
            log.error("Error updating frame", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("更新帧失败: " + e.getMessage()));
        }
    }

    @PostMapping("/settings")
    @SuppressWarnings("unchecked")
    public ResponseEntity<ApiResponse<SettingsService.Settings>> updateSettings(@RequestBody Map<String, Object> body) {
        try {
            Settings current = settingsService.getSettings();
            Settings merged = mergeMapIntoSettings(body, current);
            settingsService.updateSettings(merged);
            return ResponseEntity.ok(ApiResponse.success("设置已保存", settingsService.getSettings()));
        } catch (Exception e) {
            log.error("Error updating settings", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("保存设置失败: " + e.getMessage()));
        }
    }

    @SuppressWarnings("unchecked")
    private Settings mergeMapIntoSettings(Map<String, Object> map, Settings current) {
        Double confidence = map.containsKey("confidence") ? toDouble(map.get("confidence")) : current.getConfidence();
        Double iou = map.containsKey("iou") ? toDouble(map.get("iou")) : current.getIou();
        Integer interval = map.containsKey("interval") ? toInteger(map.get("interval")) : current.getInterval();
        Integer maxPeople = map.containsKey("maxPeople") ? toInteger(map.get("maxPeople")) : current.getMaxPeople();
        Integer cooldown = map.containsKey("cooldown") ? toInteger(map.get("cooldown")) : current.getCooldown();
        Integer fatigueThreshold = map.containsKey("fatigueThreshold") ? toInteger(map.get("fatigueThreshold")) : current.getFatigueThreshold();

        AiSensitivity aiSens = current.getAiSensitivity();
        if (map.containsKey("aiSensitivity") && map.get("aiSensitivity") instanceof Map<?, ?> aiMap) {
            AiSensitivity incoming = mapToAiSensitivity((Map<String, Object>) aiMap);
            aiSens = aiSens != null ? aiSens.merge(incoming) : incoming;
        }

        AppNotifications notifs = current.getNotifications();
        if (map.containsKey("notifications") && map.get("notifications") instanceof Map<?, ?> nMap) {
            AppNotifications incoming = mapToNotifications((Map<String, Object>) nMap);
            notifs = notifs != null ? notifs.merge(incoming) : incoming;
        }

        StorageSettings stor = current.getStorage();
        if (map.containsKey("storage") && map.get("storage") instanceof Map<?, ?> sMap) {
            StorageSettings incoming = mapToStorage((Map<String, Object>) sMap);
            stor = stor != null ? stor.merge(incoming) : incoming;
        }

        return new Settings(confidence, iou, interval, maxPeople, cooldown, fatigueThreshold,
                aiSens, notifs, stor);
    }

    private AiSensitivity mapToAiSensitivity(Map<String, Object> map) {
        return new AiSensitivity(
                map.containsKey("fightDetection") ? toInteger(map.get("fightDetection")) : null,
                map.containsKey("fallDetection") ? toInteger(map.get("fallDetection")) : null,
                map.containsKey("climbingDetection") ? toInteger(map.get("climbingDetection")) : null,
                map.containsKey("crowdGathering") ? toInteger(map.get("crowdGathering")) : null
        );
    }

    private AppNotifications mapToNotifications(Map<String, Object> map) {
        return new AppNotifications(
                map.containsKey("email") ? toBoolean(map.get("email")) : null,
                map.containsKey("sms") ? toBoolean(map.get("sms")) : null,
                map.containsKey("centralAlarm") ? toBoolean(map.get("centralAlarm")) : null
        );
    }

    private StorageSettings mapToStorage(Map<String, Object> map) {
        return new StorageSettings(
                map.containsKey("autoOverwrite") ? toBoolean(map.get("autoOverwrite")) : null
        );
    }

    private static Double toDouble(Object val) {
        if (val == null) return null;
        if (val instanceof Number n) return n.doubleValue();
        return Double.parseDouble(val.toString());
    }

    private static Integer toInteger(Object val) {
        if (val == null) return null;
        if (val instanceof Number n) return n.intValue();
        return Integer.parseInt(val.toString());
    }

    private static Boolean toBoolean(Object val) {
        if (val == null) return null;
        if (val instanceof Boolean b) return b;
        return Boolean.parseBoolean(val.toString());
    }
}
