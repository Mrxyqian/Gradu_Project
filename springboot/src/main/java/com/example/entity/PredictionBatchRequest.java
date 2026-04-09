package com.example.entity;

import java.util.List;

public class PredictionBatchRequest {
    private List<Integer> ids;
    private String modelVersion;

    public List<Integer> getIds() {
        return ids;
    }

    public void setIds(List<Integer> ids) {
        this.ids = ids;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }
}
