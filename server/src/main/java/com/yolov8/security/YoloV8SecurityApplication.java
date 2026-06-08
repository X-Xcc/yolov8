package com.yolov8.security;

import io.github.cdimascio.dotenv.Dotenv;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@SpringBootApplication
@EnableScheduling
@EnableAsync
public class YoloV8SecurityApplication extends SpringBootServletInitializer {

    static {
        loadDotEnv();
    }

    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
        return application.sources(YoloV8SecurityApplication.class);
    }

    public static void main(String[] args) {
        SpringApplication.run(YoloV8SecurityApplication.class, args);
    }

    private static void loadDotEnv() {
        // Try current dir first, then parent (for running from server/)
        Path dotenvPath = null;
        for (String candidate : new String[]{".env", "../.env"}) {
            Path p = Paths.get(candidate).normalize();
            if (Files.exists(p)) {
                dotenvPath = p;
                break;
            }
        }
        if (dotenvPath == null) return;

        try {
            Dotenv dotenv = Dotenv.configure()
                    .directory(dotenvPath.getParent() != null ? dotenvPath.getParent().toString() : ".")
                    .filename(dotenvPath.getFileName().toString())
                    .ignoreIfMissing()
                    .load();
            dotenv.entries().forEach(e -> {
                if (System.getProperty(e.getKey()) == null && System.getenv(e.getKey()) == null) {
                    System.setProperty(e.getKey(), e.getValue());
                }
            });
            System.out.println("Loaded .env from " + dotenvPath.toAbsolutePath());
        } catch (Exception e) {
            System.out.println("Warning: failed to load .env: " + e.getMessage());
        }
    }
}
