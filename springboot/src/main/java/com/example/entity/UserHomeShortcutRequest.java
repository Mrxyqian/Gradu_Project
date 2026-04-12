package com.example.entity;

import java.util.List;

public class UserHomeShortcutRequest {
    private List<String> selectedPaths;

    public List<String> getSelectedPaths() {
        return selectedPaths;
    }

    public void setSelectedPaths(List<String> selectedPaths) {
        this.selectedPaths = selectedPaths;
    }
}
