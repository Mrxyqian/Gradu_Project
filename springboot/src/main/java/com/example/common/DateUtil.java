package com.example.common;

public class DateUtil {

    private DateUtil() {
    }

    public static String convertDDMMYYYYToYYYYMMDD(String date) {
        if (date == null || date.isEmpty()) {
            return date;
        }
        String[] parts = date.split("/");
        if (parts.length == 3) {
            return parts[2] + "/" + parts[1] + "/" + parts[0];
        }
        return date;
    }

    public static String convertYYYYMMDDToDDMMYYYY(String date) {
        if (date == null || date.isEmpty()) {
            return date;
        }
        String[] parts = date.split("/");
        if (parts.length == 3) {
            return parts[2] + "/" + parts[1] + "/" + parts[0];
        }
        return date;
    }

    public static String convertYYYYMMDDToDDMMYYYYQueryPattern(String date) {
        if (date == null) {
            return null;
        }
        String normalized = date.trim();
        if (normalized.isEmpty()) {
            return normalized;
        }

        String[] parts = normalized.split("/");
        if (parts.length == 1) {
            String year = normalizeYear(parts[0]);
            return "%/" + year;
        }
        if (parts.length == 2) {
            String year = normalizeYear(parts[0]);
            String month = normalizeMonth(parts[1]);
            return "%/" + month + "/" + year;
        }
        if (parts.length == 3) {
            String year = normalizeYear(parts[0]);
            String month = normalizeMonth(parts[1]);
            String day = normalizeDay(parts[2]);
            return day + "/" + month + "/" + year;
        }
        throw new IllegalArgumentException("日期格式不正确，请使用 YYYY、YYYY/MM 或 YYYY/MM/DD");
    }

    private static String normalizeYear(String year) {
        String normalized = year == null ? "" : year.trim();
        if (!normalized.matches("\\d{4}")) {
            throw new IllegalArgumentException("年份格式不正确，请使用四位年份");
        }
        return normalized;
    }

    private static String normalizeMonth(String value) {
        return normalizeNumber(value, "月份", 12);
    }

    private static String normalizeDay(String value) {
        return normalizeNumber(value, "日期", 31);
    }

    private static String normalizeNumber(String value, String fieldName, int maxValue) {
        String normalized = value == null ? "" : value.trim();
        if (!normalized.matches("\\d{1,2}")) {
            throw new IllegalArgumentException(fieldName + "格式不正确，请使用 1-2 位数字");
        }
        int number = Integer.parseInt(normalized);
        if (number <= 0 || number > maxValue) {
            throw new IllegalArgumentException(fieldName + "超出有效范围");
        }
        return number < 10 ? "0" + number : String.valueOf(number);
    }
}
