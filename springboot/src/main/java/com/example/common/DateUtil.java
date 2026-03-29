package com.example.common;

public class DateUtil {

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
}
