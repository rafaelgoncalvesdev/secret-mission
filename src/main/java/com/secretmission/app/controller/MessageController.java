package com.secretmission.app.controller;


import com.secretmission.app.model.Message;
import com.secretmission.app.service.S3Service;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class MessageController {

    private final S3Service s3Service;

    // Dependency Injection for the S3Service
    public MessageController(S3Service s3Service) {
        this.s3Service = s3Service;
    }

    @PostMapping("/messages")
    public ResponseEntity<Map<String, String>> receiveMessage(@RequestBody Message message) {
        System.out.println("Message received in controller: " + message.getMessage());

        // Call the S3 service to perform the upload
        String fileName = s3Service.uploadMessage(message.getMessage());

        // Create a response map with status and the generated file name
        Map<String, String> response = Map.of(
                "status", "Message received and saved to S3!",
                "fileName", fileName
        );

        return ResponseEntity.ok(response);
    }
}