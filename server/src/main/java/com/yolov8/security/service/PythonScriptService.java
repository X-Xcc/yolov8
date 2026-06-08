package com.yolov8.security.service;

import com.yolov8.security.config.AppConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.Map;

@Service
public class PythonScriptService {

    private static final Logger log = LoggerFactory.getLogger(PythonScriptService.class);
    private final AppConfig appConfig;
    private volatile Process detectionProcess;

    public PythonScriptService(AppConfig appConfig) {
        this.appConfig = appConfig;
    }

    /**
     * Start Python detection in background. Returns immediately.
     */
    public synchronized Map<String, Object> startMonitoring() {
        if (detectionProcess != null && detectionProcess.isAlive()) {
            log.info("Detection already running (PID {})", detectionProcess.pid());
            return Map.of("status", "already_running", "pid", detectionProcess.pid());
        }

        String scriptPath = appConfig.getPython().getScriptPath();

        // Find project root — try current dir first, then parent
        File cwd = new File(System.getProperty("user.dir")).getAbsoluteFile();
        File projectRoot = new File(cwd, scriptPath).exists() ? cwd : cwd.getParentFile();
        File scriptFile = new File(projectRoot, scriptPath);
        if (!scriptFile.exists()) {
            log.error("Python script not found: {}", scriptPath);
            return Map.of("status", "error", "message", "Script not found: " + scriptPath);
        }

        // Find venv python in project root
        File venvPython = new File(projectRoot, ".venv/Scripts/python.exe");
        String pythonCmd = venvPython.exists() ? venvPython.getAbsolutePath() : "python";

        try {
            ProcessBuilder pb = new ProcessBuilder(pythonCmd, scriptFile.getAbsolutePath());
            pb.redirectErrorStream(true);
            pb.directory(projectRoot);

            // Activate venv environment for subprocess
            if (venvPython.exists()) {
                Map<String, String> env = pb.environment();
                File venvScripts = venvPython.getParentFile();
                env.put("VIRTUAL_ENV", venvScripts.getParentFile().getAbsolutePath());
                env.put("PATH", venvScripts.getAbsolutePath() + File.pathSeparator + env.get("PATH"));
            }

            pb.redirectOutput(ProcessBuilder.Redirect.to(new File(projectRoot, "python_detection.log")));

            log.info("Starting Python detection: {} {} (workdir={})",
                    pythonCmd, scriptFile.getAbsolutePath(), projectRoot.getAbsolutePath());
            detectionProcess = pb.start();
            log.info("Detection started with PID {}", detectionProcess.pid());

            return Map.of("status", "started", "pid", detectionProcess.pid());
        } catch (Exception e) {
            log.error("Failed to start detection", e);
            return Map.of("status", "error", "message", e.getMessage());
        }
    }

    /**
     * Stop Python detection process.
     */
    public synchronized Map<String, Object> stopMonitoring() {
        if (detectionProcess == null || !detectionProcess.isAlive()) {
            return Map.of("status", "not_running");
        }

        long pid = detectionProcess.pid();
        log.info("Stopping detection (PID {})", pid);
        detectionProcess.destroy();
        try {
            boolean exited = detectionProcess.waitFor(5, java.util.concurrent.TimeUnit.SECONDS);
            if (!exited) {
                detectionProcess.destroyForcibly();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            detectionProcess.destroyForcibly();
        }
        return Map.of("status", "stopped", "pid", pid);
    }

    /**
     * Check if detection is currently running.
     */
    public synchronized boolean isRunning() {
        return detectionProcess != null && detectionProcess.isAlive();
    }
}
