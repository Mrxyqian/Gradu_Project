-- 理赔记录表
CREATE TABLE claim_record (
    ID INT NOT NULL COMMENT '关联主数据唯一识别号',
    Cost_claims_year DECIMAL(10,2) NOT NULL COMMENT '本年度索赔总成本',
    N_claims_year INT NOT NULL COMMENT '本年度索赔次数',
    N_claims_history INT NOT NULL COMMENT '历史索赔次数',
    R_Claims_history DECIMAL(6,2) NOT NULL COMMENT '历史出险率/索赔频率比',
    Type_risk TINYINT NOT NULL COMMENT '风险类型：1=摩托车，2=货车，3=乘用车，4=农用车',
    Area TINYINT NOT NULL COMMENT '地区：0=农村，1=城市',
    PRIMARY KEY (ID),
    CONSTRAINT fk_claim_record_motor_insurance
        FOREIGN KEY (ID) REFERENCES motor_insurance(ID)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='理赔记录表';


-- 车辆信息表
CREATE TABLE vehicle_info (
    ID INT NOT NULL COMMENT '关联主数据唯一识别号',
    Type_risk TINYINT NOT NULL COMMENT '风险类型：1=摩托车，2=货车，3=乘用车，4=农用车',
    Year_matriculation INT NOT NULL COMMENT '车辆注册年份',
    Power INT NOT NULL COMMENT '马力(HP)',
    Cylinder_capacity INT NOT NULL COMMENT '气缸排量(cc)',
    Value_vehicle DECIMAL(10,2) NOT NULL COMMENT '车辆市场价值',
    N_doors INT NOT NULL COMMENT '车门数',
    Type_fuel CHAR(1) NOT NULL COMMENT '燃料类型：P=汽油，D=柴油',
    Length DECIMAL(5,2) DEFAULT NULL COMMENT '车长(米)',
    Weight INT DEFAULT NULL COMMENT '车重(千克)',
    PRIMARY KEY (ID),
    CONSTRAINT fk_vehicle_info_motor_insurance
        FOREIGN KEY (ID) REFERENCES motor_insurance(ID)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车辆信息表';
