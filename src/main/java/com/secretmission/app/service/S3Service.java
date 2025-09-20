package com.secretmission.app.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.UUID;

@Service
public class S3Service {

    private final S3Client s3Client;
    private final String bucketName;

    public S3Service(S3Client s3Client, @Value("${app.s3.bucket-name}") String bucketName){
        this.s3Client = s3Client;
        this.bucketName = bucketName;
    }

    public String uploadMessage(String messageContent){
        String fileName = Instant.now().toString() + "-" + UUID.randomUUID() + ".txt";

        PutObjectRequest request = PutObjectRequest.builder()
                .bucket(bucketName)
                .key(fileName)
                .build();

        s3Client.putObject(request, RequestBody.fromString(messageContent, StandardCharsets.UTF_8));

        System.out.println("Message sent to AWS S3 Bucket with the following filename: " + fileName);

        return fileName;
    }
}
