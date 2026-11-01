-- =====================================================================
-- COLLEGE MANAGEMENT SYSTEM - TWO-TIER ARCHITECTURE
-- Amazon RDS MySQL Database Schema
-- Database Name: college_management
-- Region: AWS ap-south-1 (Mumbai)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `college_management`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `college_management`;

-- Disable foreign key checks during creation
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- 1. ROLES
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `role_name` VARCHAR(50) NOT NULL UNIQUE,
  `description` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 2. PERMISSIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `permissions`;
CREATE TABLE `permissions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `permission_name` VARCHAR(100) NOT NULL UNIQUE,
  `description` VARCHAR(255) NULL,
  `category` VARCHAR(50) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 3. ROLE_PERMISSIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `role_permissions`;
CREATE TABLE `role_permissions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `role_id` INT NOT NULL,
  `permission_id` INT NOT NULL,
  CONSTRAINT `uq_role_permission` UNIQUE (`role_id`, `permission_id`),
  CONSTRAINT `fk_rp_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_rp_permission` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 4. USERS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(80) NOT NULL UNIQUE,
  `email` VARCHAR(120) NOT NULL UNIQUE,
  `password_hash` VARCHAR(256) NOT NULL,
  `role_id` INT NOT NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `first_name` VARCHAR(50) NOT NULL,
  `last_name` VARCHAR(50) NOT NULL,
  `phone` VARCHAR(20) NULL,
  `profile_photo_key` VARCHAR(512) NULL COMMENT 'Amazon S3 Object Key',
  `last_login` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_users_email` (`email`),
  INDEX `ix_users_username` (`username`),
  CONSTRAINT `fk_users_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 5. ACADEMIC YEARS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `academic_years`;
CREATE TABLE `academic_years` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `year_label` VARCHAR(20) NOT NULL UNIQUE COMMENT 'e.g. 2024-2025',
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `is_current` BOOLEAN NOT NULL DEFAULT FALSE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 6. DEPARTMENTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `departments`;
CREATE TABLE `departments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `department_name` VARCHAR(100) NOT NULL UNIQUE,
  `department_code` VARCHAR(20) NOT NULL UNIQUE,
  `description` TEXT NULL,
  `hod_faculty_id` INT NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 7. SEMESTERS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `semesters`;
CREATE TABLE `semesters` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `semester_number` INT NOT NULL COMMENT '1 to 8',
  `semester_name` VARCHAR(50) NULL,
  `academic_year_id` INT NOT NULL,
  `department_id` INT NULL,
  `start_date` DATE NULL,
  `end_date` DATE NULL,
  `is_current` BOOLEAN NOT NULL DEFAULT FALSE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_sem_academic_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sem_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 8. SUBJECTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `subjects`;
CREATE TABLE `subjects` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `subject_name` VARCHAR(100) NOT NULL,
  `subject_code` VARCHAR(20) NOT NULL UNIQUE,
  `department_id` INT NOT NULL,
  `semester_id` INT NULL,
  `credits` INT NOT NULL DEFAULT 4,
  `max_internal_marks` INT NOT NULL DEFAULT 40,
  `max_external_marks` INT NOT NULL DEFAULT 60,
  `max_practical_marks` INT NOT NULL DEFAULT 0,
  `subject_type` ENUM('theory', 'practical', 'both') NOT NULL DEFAULT 'theory',
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_subjects_code` (`subject_code`),
  CONSTRAINT `fk_sub_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sub_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 9. FACULTY
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `faculty`;
CREATE TABLE `faculty` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL UNIQUE,
  `employee_id` VARCHAR(50) NOT NULL UNIQUE,
  `department_id` INT NOT NULL,
  `designation` VARCHAR(100) NULL,
  `specialization` VARCHAR(150) NULL,
  `qualification` VARCHAR(100) NULL,
  `date_of_joining` DATE NULL,
  `employment_type` ENUM('full-time', 'part-time', 'visiting') NOT NULL DEFAULT 'full-time',
  `experience_years` INT DEFAULT 0,
  `profile_photo_key` VARCHAR(512) NULL COMMENT 'Amazon S3 Object Key',
  `is_hod` BOOLEAN NOT NULL DEFAULT FALSE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_faculty_empid` (`employee_id`),
  CONSTRAINT `fk_faculty_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_faculty_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add deferred foreign key for HOD in departments table
ALTER TABLE `departments`
  ADD CONSTRAINT `fk_dept_hod` FOREIGN KEY (`hod_faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL;

-- ---------------------------------------------------------------------
-- 10. CLASS_SECTIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `class_sections`;
CREATE TABLE `class_sections` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `section_name` VARCHAR(50) NOT NULL COMMENT 'e.g. CS-A',
  `department_id` INT NOT NULL,
  `semester_id` INT NOT NULL,
  `academic_year_id` INT NOT NULL,
  `max_students` INT NOT NULL DEFAULT 60,
  `room_number` VARCHAR(30) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_cs_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_cs_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_cs_academic_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 11. STUDENTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `students`;
CREATE TABLE `students` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL UNIQUE,
  `student_roll_number` VARCHAR(50) NOT NULL UNIQUE,
  `registration_number` VARCHAR(50) NOT NULL UNIQUE,
  `department_id` INT NOT NULL,
  `current_semester_id` INT NULL,
  `current_class_section_id` INT NULL,
  `date_of_birth` DATE NULL,
  `gender` VARCHAR(10) NULL,
  `blood_group` VARCHAR(5) NULL,
  `address` TEXT NULL,
  `city` VARCHAR(60) NULL,
  `state` VARCHAR(60) NULL,
  `pincode` VARCHAR(10) NULL,
  `country` VARCHAR(60) DEFAULT 'India',
  `guardian_name` VARCHAR(100) NULL,
  `guardian_phone` VARCHAR(20) NULL,
  `guardian_email` VARCHAR(120) NULL,
  `guardian_relation` VARCHAR(30) NULL,
  `admission_date` DATE NULL,
  `academic_status` ENUM('active', 'suspended', 'graduated', 'dropped') NOT NULL DEFAULT 'active',
  `profile_photo_key` VARCHAR(512) NULL COMMENT 'Amazon S3 Object Key',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_students_roll` (`student_roll_number`),
  CONSTRAINT `fk_student_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_student_dept` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_student_semester` FOREIGN KEY (`current_semester_id`) REFERENCES `semesters` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_student_class_section` FOREIGN KEY (`current_class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 12. FACULTY_ASSIGNMENTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `faculty_assignments`;
CREATE TABLE `faculty_assignments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `faculty_id` INT NOT NULL,
  `subject_id` INT NOT NULL,
  `class_section_id` INT NOT NULL,
  `academic_year_id` INT NOT NULL,
  `assigned_date` DATE NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_faculty_assignment` UNIQUE (`faculty_id`, `subject_id`, `class_section_id`, `academic_year_id`),
  CONSTRAINT `fk_fa_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fa_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fa_class` FOREIGN KEY (`class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fa_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 13. STUDENT_ENROLLMENTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `student_enrollments`;
CREATE TABLE `student_enrollments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `student_id` INT NOT NULL,
  `class_section_id` INT NOT NULL,
  `academic_year_id` INT NOT NULL,
  `enrollment_date` DATE NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_student_enrollment` UNIQUE (`student_id`, `class_section_id`, `academic_year_id`),
  CONSTRAINT `fk_se_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_se_class` FOREIGN KEY (`class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_se_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 14. ATTENDANCE_SESSIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `attendance_sessions`;
CREATE TABLE `attendance_sessions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `subject_id` INT NOT NULL,
  `class_section_id` INT NOT NULL,
  `faculty_id` INT NULL,
  `session_date` DATE NOT NULL,
  `session_type` ENUM('lecture', 'lab', 'tutorial') NOT NULL DEFAULT 'lecture',
  `start_time` TIME NULL,
  `end_time` TIME NULL,
  `academic_year_id` INT NULL,
  `semester_id` INT NULL,
  `notes` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `uq_attendance_session` UNIQUE (`subject_id`, `class_section_id`, `session_date`, `session_type`),
  CONSTRAINT `fk_as_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_as_class` FOREIGN KEY (`class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_as_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 15. ATTENDANCE_RECORDS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `attendance_records`;
CREATE TABLE `attendance_records` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `session_id` INT NOT NULL,
  `student_id` INT NOT NULL,
  `status` ENUM('Present', 'Absent', 'Late', 'Leave') NOT NULL DEFAULT 'Present',
  `remarks` VARCHAR(255) NULL,
  `marked_by_faculty_id` INT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `uq_session_student_att` UNIQUE (`session_id`, `student_id`),
  INDEX `ix_att_student_session` (`student_id`, `session_id`),
  CONSTRAINT `fk_ar_session` FOREIGN KEY (`session_id`) REFERENCES `attendance_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ar_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ar_faculty` FOREIGN KEY (`marked_by_faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 16. EXAMS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `exams`;
CREATE TABLE `exams` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(200) NOT NULL,
  `description` TEXT NULL,
  `subject_id` INT NOT NULL,
  `class_section_id` INT NULL,
  `created_by_faculty_id` INT NULL,
  `academic_year_id` INT NULL,
  `semester_id` INT NULL,
  `exam_type` VARCHAR(30) NOT NULL DEFAULT 'MCQ',
  `duration_minutes` INT NOT NULL DEFAULT 60,
  `start_time` DATETIME NOT NULL,
  `end_time` DATETIME NOT NULL,
  `total_marks` INT NOT NULL DEFAULT 100,
  `passing_marks` INT NOT NULL DEFAULT 40,
  `max_attempts` INT NOT NULL DEFAULT 1,
  `status` ENUM('draft', 'published', 'active', 'closed') NOT NULL DEFAULT 'draft',
  `instructions` TEXT NULL,
  `shuffle_questions` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` DATETIME NULL,
  CONSTRAINT `fk_exam_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exam_class` FOREIGN KEY (`class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_exam_faculty` FOREIGN KEY (`created_by_faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 17. QUESTIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `questions`;
CREATE TABLE `questions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `exam_id` INT NOT NULL,
  `question_text` TEXT NOT NULL,
  `question_type` VARCHAR(30) NOT NULL DEFAULT 'MCQ',
  `marks` FLOAT NOT NULL DEFAULT 1.0,
  `order_number` INT NOT NULL DEFAULT 1,
  `explanation` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_q_exam` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 18. QUESTION_OPTIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `question_options`;
CREATE TABLE `question_options` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `question_id` INT NOT NULL,
  `option_text` TEXT NOT NULL,
  `is_correct` BOOLEAN NOT NULL DEFAULT FALSE,
  `order_number` INT NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_qo_question` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 19. EXAM_ATTEMPTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `exam_attempts`;
CREATE TABLE `exam_attempts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `exam_id` INT NOT NULL,
  `student_id` INT NOT NULL,
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `submitted_at` DATETIME NULL,
  `time_taken_minutes` INT NULL,
  `score_obtained` FLOAT DEFAULT 0.0,
  `total_marks_attempted` FLOAT DEFAULT 0.0,
  `percentage` FLOAT DEFAULT 0.0,
  `is_passed` BOOLEAN DEFAULT FALSE,
  `status` ENUM('in_progress', 'submitted', 'auto_submitted') NOT NULL DEFAULT 'in_progress',
  `attempt_number` INT NOT NULL DEFAULT 1,
  `ip_address` VARCHAR(45) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_exam_student_attempt` UNIQUE (`exam_id`, `student_id`, `attempt_number`),
  CONSTRAINT `fk_ea_exam` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ea_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 20. ATTEMPT_ANSWERS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `attempt_answers`;
CREATE TABLE `attempt_answers` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `attempt_id` INT NOT NULL,
  `question_id` INT NOT NULL,
  `selected_option_id` INT NULL,
  `is_correct` BOOLEAN NULL,
  `marks_obtained` FLOAT DEFAULT 0.0,
  `answered_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_aa_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `exam_attempts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_aa_question` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_aa_option` FOREIGN KEY (`selected_option_id`) REFERENCES `question_options` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 21. RESULTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `results`;
CREATE TABLE `results` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `student_id` INT NOT NULL,
  `subject_id` INT NOT NULL,
  `semester_id` INT NOT NULL,
  `academic_year_id` INT NOT NULL,
  `internal_marks` FLOAT DEFAULT 0.0,
  `external_marks` FLOAT DEFAULT 0.0,
  `practical_marks` FLOAT DEFAULT 0.0,
  `total_marks` FLOAT DEFAULT 0.0,
  `max_total_marks` FLOAT DEFAULT 100.0,
  `percentage` FLOAT DEFAULT 0.0,
  `grade` VARCHAR(10) NULL,
  `is_passed` BOOLEAN DEFAULT FALSE,
  `result_status` ENUM('pass', 'fail', 'absent', 'withheld') NOT NULL DEFAULT 'pass',
  `is_published` BOOLEAN NOT NULL DEFAULT FALSE,
  `published_at` DATETIME NULL,
  `remarks` VARCHAR(255) NULL,
  `entered_by_faculty_id` INT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `uq_result_student_sub_sem` UNIQUE (`student_id`, `subject_id`, `semester_id`, `academic_year_id`),
  CONSTRAINT `fk_res_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_res_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_res_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_res_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_res_faculty` FOREIGN KEY (`entered_by_faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 22. FEE_RECORDS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `fee_records`;
CREATE TABLE `fee_records` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `student_id` INT NOT NULL,
  `semester_id` INT NOT NULL,
  `academic_year_id` INT NOT NULL,
  `fee_type` ENUM('tuition', 'hostel', 'library', 'exam', 'transport', 'other') NOT NULL DEFAULT 'tuition',
  `description` VARCHAR(255) NULL,
  `total_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `amount_paid` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `due_date` DATE NOT NULL,
  `payment_status` ENUM('pending', 'partial', 'paid', 'overdue', 'waived') NOT NULL DEFAULT 'pending',
  `waiver_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `waiver_reason` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_fr_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fr_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_fr_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 23. FEE_PAYMENTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `fee_payments`;
CREATE TABLE `fee_payments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `fee_record_id` INT NOT NULL,
  `payment_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `amount_paid` DECIMAL(10,2) NOT NULL,
  `payment_mode` ENUM('cash', 'online', 'cheque', 'dd', 'upi') NOT NULL DEFAULT 'online',
  `transaction_reference` VARCHAR(100) NULL,
  `receipt_number` VARCHAR(50) NOT NULL UNIQUE,
  `remarks` VARCHAR(255) NULL,
  `received_by_user_id` INT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_fp_fee_record` FOREIGN KEY (`fee_record_id`) REFERENCES `fee_records` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fp_user` FOREIGN KEY (`received_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 24. ASSIGNMENTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `assignments`;
CREATE TABLE `assignments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(200) NOT NULL,
  `description` TEXT NULL,
  `subject_id` INT NOT NULL,
  `class_section_id` INT NOT NULL,
  `faculty_id` INT NOT NULL,
  `due_date` DATETIME NOT NULL,
  `max_marks` INT NOT NULL DEFAULT 100,
  `instructions` TEXT NULL,
  `file_key` VARCHAR(512) NULL COMMENT 'Amazon S3 Object Key',
  `file_name` VARCHAR(255) NULL,
  `file_size` INT NULL,
  `status` ENUM('draft', 'published', 'closed') NOT NULL DEFAULT 'published',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` DATETIME NULL,
  CONSTRAINT `fk_assign_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_assign_class` FOREIGN KEY (`class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_assign_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 25. ASSIGNMENT_SUBMISSIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `assignment_submissions`;
CREATE TABLE `assignment_submissions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `assignment_id` INT NOT NULL,
  `student_id` INT NOT NULL,
  `file_key` VARCHAR(512) NOT NULL COMMENT 'Amazon S3 Object Key',
  `file_name` VARCHAR(255) NOT NULL,
  `file_size` INT NULL,
  `submitted_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `marks_obtained` FLOAT NULL,
  `feedback` TEXT NULL,
  `submission_status` ENUM('submitted', 'late', 'graded') NOT NULL DEFAULT 'submitted',
  `graded_by_faculty_id` INT NULL,
  `graded_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `uq_assignment_student_sub` UNIQUE (`assignment_id`, `student_id`),
  CONSTRAINT `fk_asub_assignment` FOREIGN KEY (`assignment_id`) REFERENCES `assignments` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_asub_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_asub_faculty` FOREIGN KEY (`graded_by_faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 26. STUDY_MATERIALS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `study_materials`;
CREATE TABLE `study_materials` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(200) NOT NULL,
  `description` TEXT NULL,
  `subject_id` INT NOT NULL,
  `class_section_id` INT NULL,
  `faculty_id` INT NOT NULL,
  `file_key` VARCHAR(512) NOT NULL COMMENT 'Amazon S3 Object Key',
  `file_name` VARCHAR(255) NOT NULL,
  `file_size` INT NULL,
  `file_type` VARCHAR(50) NULL,
  `material_type` ENUM('notes', 'video_link', 'reference', 'question_bank', 'syllabus') NOT NULL DEFAULT 'notes',
  `is_visible` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_sm_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sm_class` FOREIGN KEY (`class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_sm_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 27. NOTIFICATIONS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(200) NOT NULL,
  `message` TEXT NOT NULL,
  `notification_type` ENUM('academic', 'exam', 'fee', 'general', 'urgent') NOT NULL DEFAULT 'general',
  `sender_id` INT NOT NULL,
  `target_role` ENUM('all', 'admin', 'faculty', 'student') NULL,
  `target_user_id` INT NULL,
  `target_class_section_id` INT NULL,
  `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
  `read_at` DATETIME NULL,
  `expires_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_notif_target_user` (`target_user_id`, `is_read`),
  INDEX `ix_notif_created_at` (`created_at`),
  CONSTRAINT `fk_notif_sender` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_notif_target_user` FOREIGN KEY (`target_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_notif_class` FOREIGN KEY (`target_class_section_id`) REFERENCES `class_sections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 28. AUDIT_LOGS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NULL,
  `action` VARCHAR(100) NOT NULL,
  `resource_type` VARCHAR(50) NOT NULL,
  `resource_id` VARCHAR(50) NULL,
  `old_values` TEXT NULL,
  `new_values` TEXT NULL,
  `ip_address` VARCHAR(45) NULL,
  `user_agent` VARCHAR(255) NULL,
  `status` ENUM('success', 'failure') NOT NULL DEFAULT 'success',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_audit_user_created` (`user_id`, `created_at`),
  INDEX `ix_audit_resource` (`resource_type`, `resource_id`),
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 29. STUDENT_DOCUMENTS
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `student_documents`;
CREATE TABLE `student_documents` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `student_id` INT NOT NULL,
  `document_type` ENUM('photo', 'certificate', 'id_proof', 'marksheet', 'other') NOT NULL DEFAULT 'other',
  `document_name` VARCHAR(255) NOT NULL,
  `file_key` VARCHAR(512) NOT NULL COMMENT 'Amazon S3 Object Key',
  `file_name` VARCHAR(255) NOT NULL,
  `file_size` INT NULL,
  `uploaded_by_user_id` INT NULL,
  `verification_status` ENUM('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  `verified_by_user_id` INT NULL,
  `verified_at` DATETIME NULL,
  `remarks` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_sdoc_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sdoc_uploaded_by` FOREIGN KEY (`uploaded_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_sdoc_verified_by` FOREIGN KEY (`verified_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- SEED DATA: CORE ROLES
-- ---------------------------------------------------------------------
INSERT INTO `roles` (`id`, `role_name`, `description`) VALUES
  (1, 'Admin', 'Superuser with unrestricted access across all tiers, modules, and configurations.'),
  (2, 'Faculty', 'Broad academic management permissions for assigned departments, classes and subjects.'),
  (3, 'Student', 'Restricted access to personal academic records, attendance, and MCQ examinations.')
ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

-- ---------------------------------------------------------------------
-- SEED DATA: PERMISSIONS
-- ---------------------------------------------------------------------
INSERT INTO `permissions` (`permission_name`, `category`, `description`) VALUES
  ('view_students', 'student', 'View student directories and records'),
  ('manage_students', 'student', 'Create, update, and manage student accounts'),
  ('create_student', 'student', 'Register new student accounts'),
  ('edit_student', 'student', 'Edit student academic and biographical details'),
  ('delete_student', 'student', 'Deactivate or delete student accounts'),
  ('view_own_profile', 'student', 'View personal student profile'),
  ('edit_own_profile', 'student', 'Update personal photo and contact details'),
  ('view_faculty', 'faculty', 'View faculty directories and records'),
  ('manage_faculty', 'faculty', 'Create, update, and manage faculty accounts'),
  ('create_faculty', 'faculty', 'Register new faculty accounts'),
  ('edit_faculty', 'faculty', 'Edit faculty details and designations'),
  ('delete_faculty', 'faculty', 'Deactivate or delete faculty accounts'),
  ('view_courses', 'academic', 'View departments and course structures'),
  ('manage_courses', 'academic', 'Create and modify departments'),
  ('view_subjects', 'academic', 'View subjects and syllabi'),
  ('manage_subjects', 'academic', 'Add and update curriculum subjects'),
  ('view_attendance', 'attendance', 'View attendance logs and sessions'),
  ('manage_attendance', 'attendance', 'Configure attendance policies'),
  ('mark_attendance', 'attendance', 'Mark student daily attendance'),
  ('edit_attendance', 'attendance', 'Update existing attendance records'),
  ('view_own_attendance', 'attendance', 'View own attendance percentage'),
  ('view_exams', 'exam', 'View examination schedule and details'),
  ('manage_exams', 'exam', 'Configure exams and question banks'),
  ('create_exam', 'exam', 'Create online MCQ examinations'),
  ('edit_exam', 'exam', 'Edit exam questions and schedules'),
  ('publish_exam', 'exam', 'Publish exams to students'),
  ('take_exam', 'exam', 'Attempt online MCQ examinations'),
  ('view_results', 'results', 'View academic marks and grades'),
  ('manage_results', 'results', 'Enter and evaluate student marks'),
  ('enter_marks', 'results', 'Enter internal and external examination scores'),
  ('publish_results', 'results', 'Publish semester results and transcripts'),
  ('view_own_results', 'results', 'View own published semester results'),
  ('view_fees', 'fees', 'View tuition fee records and balances'),
  ('manage_fees', 'fees', 'Configure fee structures and penalties'),
  ('collect_fees', 'fees', 'Record fee payments and receipts'),
  ('view_own_fees', 'fees', 'View own fee status and payment history'),
  ('view_assignments', 'assignments', 'View coursework assignments'),
  ('manage_assignments', 'assignments', 'Create assignments and grade submissions'),
  ('submit_assignment', 'assignments', 'Upload assignment solutions to S3'),
  ('view_materials', 'materials', 'View and download course notes'),
  ('upload_materials', 'materials', 'Upload lecture materials to Amazon S3'),
  ('send_notifications', 'notifications', 'Broadcast institutional notices'),
  ('view_notifications', 'notifications', 'View received notifications'),
  ('view_audit_log', 'system', 'Inspect immutable audit logs'),
  ('manage_settings', 'system', 'Configure system settings and security policies')
ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);
