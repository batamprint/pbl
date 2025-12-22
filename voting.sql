-- phpMyAdmin SQL Dump
-- version 5.2.3deb1
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Dec 22, 2025 at 10:51 AM
-- Server version: 11.8.3-MariaDB-1+b1 from Debian
-- PHP Version: 8.4.11

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `voting`
--

-- --------------------------------------------------------

--
-- Table structure for table `admin`
--

CREATE TABLE `admin` (
  `id` int(11) NOT NULL,
  `username` varchar(50) DEFAULT NULL,
  `password` char(32) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `admin`
--

INSERT INTO `admin` (`id`, `username`, `password`) VALUES
(1, 'admin', '0192023a7bbd73250516f069df18b500');

-- --------------------------------------------------------

--
-- Table structure for table `kandidat`
--

CREATE TABLE `kandidat` (
  `id` int(11) NOT NULL,
  `nama` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `kandidat`
--

INSERT INTO `kandidat` (`id`, `nama`) VALUES
(1, 'Aulia imam nugroho'),
(2, 'adawas'),
(3, 'derrr');

-- --------------------------------------------------------

--
-- Table structure for table `siswa_request`
--

CREATE TABLE `siswa_request` (
  `id` int(11) NOT NULL,
  `no_wa` varchar(20) DEFAULT NULL,
  `kode` varchar(6) DEFAULT NULL,
  `waktu_request` timestamp NOT NULL DEFAULT current_timestamp(),
  `sudah_vote` tinyint(1) DEFAULT 0,
  `tx_hash` varchar(70) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `siswa_request`
--

INSERT INTO `siswa_request` (`id`, `no_wa`, `kode`, `waktu_request`, `sudah_vote`, `tx_hash`) VALUES
(1, '082286408602', '117283', '2025-12-22 10:45:46', 1, '0x37d082f4d29a45e11230a65ed5f478eed6c492d0016ecf35daef075961bad7e4'),
(2, '082286408600', '947747', '2025-12-22 10:49:40', 1, '0xfcfa5cc60a4ebde03145f81421f7a2ca9a98bf5144f5211cb68b4a147573d2e7'),
(3, '088289721812', '766212', '2025-12-22 10:49:57', 1, '0xfed6e6d3fab6c73ace681616cc79c4dbd706900342f79e6760604000bdab7180');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `siswa_request`
--
ALTER TABLE `siswa_request`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `siswa_request`
--
ALTER TABLE `siswa_request`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
