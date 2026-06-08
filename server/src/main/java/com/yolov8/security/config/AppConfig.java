package com.yolov8.security.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "app")
public class AppConfig {

    private FileConfig file = new FileConfig();
    private MonitorConfig monitor = new MonitorConfig();
    private PythonConfig python = new PythonConfig();
    private CleanupConfig cleanup = new CleanupConfig();
    private QwenVLConfig qwenVl = new QwenVLConfig();
    private Go2rtcConfig go2rtc = new Go2rtcConfig();
    private boolean demoMode = false;
    private String apiKey;
    private String jwtSecret;

    @Data
    public static class FileConfig {
        private String uploadDir;
        private String videoDir;
        private String modelDir;
        private String resultDir;
    }

    @Data
    public static class MonitorConfig {
        private int timeout = 300;
        private int maxRecentDetections = 20;
        private int maxRecentFrames = 5;
    }

    @Data
    public static class PythonConfig {
        private String scriptPath;
        private String executable;
    }

    @Data
    public static class QwenVLConfig {
        private String serviceUrl = "http://127.0.0.1:5002";
        private String modelPath = "./models/Qwen2.5-VL-7B-Instruct";
        private int timeout = 30000;
        private int maxRetries = 3;
    }

    @Data
    public static class CleanupConfig {
        private int retentionDays = 7;
    }

    @Data
    public static class Go2rtcConfig {
        private String binaryPath = "bin/go2rtc.exe";
        private String apiHost = "http://127.0.0.1:1984";
        private String rtspHost = "rtsp://127.0.0.1:8554";
        private int apiPort = 1984;
        private int rtspPort = 8554;
        private int webrtcPort = 8555;
    }
}