package com.example.entity;

import java.util.List;

public class AnalyticsQueryRequest {
    private String subject;
    private String groupBy;
    private List<String> metrics;
    private String sortBy;
    private String sortOrder;
    private Integer topN;
    private AnalyticsFilters filters;

    public String getSubject() {
        return subject;
    }

    public void setSubject(String subject) {
        this.subject = subject;
    }

    public String getGroupBy() {
        return groupBy;
    }

    public void setGroupBy(String groupBy) {
        this.groupBy = groupBy;
    }

    public List<String> getMetrics() {
        return metrics;
    }

    public void setMetrics(List<String> metrics) {
        this.metrics = metrics;
    }

    public String getSortBy() {
        return sortBy;
    }

    public void setSortBy(String sortBy) {
        this.sortBy = sortBy;
    }

    public String getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(String sortOrder) {
        this.sortOrder = sortOrder;
    }

    public Integer getTopN() {
        return topN;
    }

    public void setTopN(Integer topN) {
        this.topN = topN;
    }

    public AnalyticsFilters getFilters() {
        return filters;
    }

    public void setFilters(AnalyticsFilters filters) {
        this.filters = filters;
    }
}
