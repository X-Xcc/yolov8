package com.yolov8.security.controller;

import com.yolov8.security.model.ApiResponse;
import com.yolov8.security.service.CameraConfigService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class CameraConfigController {

    private static final Logger log = LoggerFactory.getLogger(CameraConfigController.class);
    private final CameraConfigService cameraConfigService;

    public CameraConfigController(CameraConfigService cameraConfigService) {
        this.cameraConfigService = cameraConfigService;
    }

    @GetMapping("/camera_config")
    public ResponseEntity<ApiResponse<List<CameraConfigService.Camera>>> getCameraConfig() {
        try {
            List<CameraConfigService.Camera> cameras = cameraConfigService.getAllCameras();
            return ResponseEntity.ok(ApiResponse.success(cameras));
        } catch (Exception e) {
            log.error("Error getting camera config", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("读取摄像头配置失败: " + e.getMessage()));
        }
    }

    @PostMapping("/camera_config")
    public ResponseEntity<ApiResponse<CameraConfigService.Camera>> addCamera(@RequestBody CameraConfigService.Camera camera) {
        try {
            CameraConfigService.Camera added = cameraConfigService.addCamera(camera);
            return ResponseEntity.ok(ApiResponse.success("摄像头已添加", added));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
        } catch (Exception e) {
            log.error("Error adding camera", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("添加摄像头失败: " + e.getMessage()));
        }
    }

    @PutMapping("/camera_config/{id}")
    public ResponseEntity<ApiResponse<CameraConfigService.Camera>> updateCamera(
            @PathVariable String id, @RequestBody CameraConfigService.Camera camera) {
        try {
            CameraConfigService.Camera updated = cameraConfigService.updateCamera(id, camera);
            return ResponseEntity.ok(ApiResponse.success("摄像头已更新", updated));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
        } catch (Exception e) {
            log.error("Error updating camera", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("更新摄像头失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/camera_config")
    public ResponseEntity<ApiResponse<Map<String, Object>>> deleteAllCameras() {
        try {
            cameraConfigService.deleteAllCameras();
            return ResponseEntity.ok(ApiResponse.success("所有摄像头已清空", Map.of("deleted", true)));
        } catch (Exception e) {
            log.error("Error clearing cameras", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("清空摄像头失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/camera_config/{id}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> deleteCamera(@PathVariable String id) {
        try {
            boolean deleted = cameraConfigService.deleteCamera(id);
            if (deleted) {
                return ResponseEntity.ok(ApiResponse.success("摄像头已删除", Map.of("deleted", true)));
            } else {
                return ResponseEntity.badRequest().body(ApiResponse.error("摄像头不存在: " + id));
            }
        } catch (Exception e) {
            log.error("Error deleting camera", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("删除摄像头失败: " + e.getMessage()));
        }
    }

    @PostMapping("/camera_config/batch")
    public ResponseEntity<ApiResponse<Map<String, Object>>> batchAddCameras(
            @RequestBody List<CameraConfigService.Camera> cameras) {
        int added = 0;
        List<String> errors = new ArrayList<>();
        for (CameraConfigService.Camera camera : cameras) {
            try {
                cameraConfigService.addCamera(camera);
                added++;
            } catch (Exception e) {
                errors.add(camera.getName() + ": " + e.getMessage());
            }
        }
        return ResponseEntity.ok(ApiResponse.success(Map.of(
            "added", added,
            "errors", errors
        )));
    }

    @PostMapping("/camera_config/test")
    public ResponseEntity<Map<String, Object>> testCameraConnection(@RequestBody Map<String, String> body) {
        String type = body.getOrDefault("type", "");
        String address = body.getOrDefault("address", "");

        if (address == null || address.isBlank()) {
            return ResponseEntity.ok(Map.of("reachable", false, "message", "地址不能为空"));
        }

        Map<String, Object> result;

        switch (type) {
            case "http_snapshot" -> {
                try {
                    URL url = new URL(address);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("HEAD");
                    conn.setConnectTimeout(5000);
                    conn.setReadTimeout(5000);
                    int code = conn.getResponseCode();
                    boolean reachable = code >= 200 && code < 400;
                    result = Map.of("reachable", reachable,
                            "message", reachable
                                    ? "HTTP连接成功 (HTTP " + code + ")"
                                    : "HTTP连接失败: HTTP " + code);
                } catch (Exception e) {
                    result = Map.of("reachable", false,
                            "message", "HTTP连接失败: " + e.getMessage());
                }
            }
            case "rtsp" -> {
                boolean valid = address.startsWith("rtsp://");
                result = Map.of("reachable", valid,
                        "message", valid
                                ? "RTSP地址格式正确（完整测试需Python检测服务）"
                                : "RTSP地址格式无效");
            }
            case "usb" -> {
                boolean valid;
                try {
                    Integer.parseInt(address.trim());
                    valid = true;
                } catch (NumberFormatException e) {
                    valid = false;
                }
                result = Map.of("reachable", valid,
                        "message", valid
                                ? "USB设备索引有效（完整测试需Python检测服务）"
                                : "USB设备索引必须为数字");
            }
            default -> {
                result = Map.of("reachable", false,
                        "message", "未知摄像头类型: " + type);
            }
        }

        return ResponseEntity.ok(result);
    }
}
