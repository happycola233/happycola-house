---
title: 稀疏文件介绍
date: 2024-07-24 13:12:17
tags:
  - 技术
  - Windows
  - 知识
categories:
  - 技术
description: 这里是一篇关于稀疏文件的介绍awa
cover: /img/posts/Sparse-File-Management-and-Usage-Guide_cover.png
permalink:
---


# 稀疏文件介绍

**稀疏文件**（Sparse File）是一种特殊的文件类型，它允许文件系统只为实际使用的部分分配磁盘空间，而未使用的部分不占用磁盘空间。这在需要创建大文件但不希望实际占用大量磁盘空间时非常有用。本文将介绍如何使用 `fsutil` 命令在 Windows 操作系统上创建和管理稀疏文件。

> **占位符文件**通过云存储客户端在本地创建小文件，实际内容存储在云端，原理与**稀疏文件**相似，但它们的用途和工作机制有显著区别。

## 基本概念

### 什么是稀疏文件？

稀疏文件是一种文件系统功能，通过将文件中的某些部分标记为“**稀疏**”，文件系统可以只为实际使用的部分分配磁盘空间，未使用的部分则不会占用物理存储。当读取这些未分配区域时，系统会返回零字节。

### 稀疏文件的优点

- **节省磁盘空间**：只为实际存储的数据分配空间。
- **提高效率**：适用于数据库、虚拟磁盘映像等场景。
- **灵活性**：在需要大文件但不希望占用大量磁盘空间的情况下非常有用。

## 创建和管理稀疏文件

### 1. 创建空文件

首先，使用 `fsutil file createnew` 命令创建一个指定大小的空文件：

```cmd
fsutil file createnew <file_name> <length>
```

- `<file_name>`：要创建的文件的路径和名称。
- `<length>`：文件的大小，以字节为单位。

#### 示例

创建一个大小为 100 MB 的新文件：

```cmd
fsutil file createnew C:\Test\sparsefile.txt 104857600
```

### 2. 将文件标记为稀疏文件

接下来，使用 `fsutil sparse setflag` 命令将文件标记为稀疏文件：

```cmd
fsutil sparse setflag <file_name>
```

#### 示例

```cmd
fsutil sparse setflag C:\Test\sparsefile.txt
```

### 3. 分配稀疏区域

使用 `fsutil sparse setrange` 命令为文件分配稀疏区域：

```cmd
fsutil sparse setrange <file_name> <offset> <length>
```

- `<offset>`：开始位置（字节）。
- `<length>`：稀疏区域的长度（字节）。

#### 示例

为 `sparsefile.txt` 文件的前 100 MB 分配稀疏区域：

```cmd
fsutil sparse setrange C:\Test\sparsefile.txt 0 104857600
```

### 4. （可缺省）检查文件是否为稀疏文件

使用 `fsutil sparse queryflag` 命令检查文件是否被标记为稀疏文件：

```cmd
fsutil sparse queryflag <file_name>
```

#### 示例

```cmd
fsutil sparse queryflag C:\Test\sparsefile.txt
```

## 对任意文件执行 `fsutil sparse setrange` 

对任意文件执行 `fsutil sparse setrange` 命令不会直接清空文件的数据，但会将指定范围内的数据标记为稀疏区域，从而变成<b>{% span red, 零字节 %}</b>（空数据），<b>{% span red, 此操作不可逆 %}</b>！

#### 示例

假设有一个文件 `C:\Test\normalfile.txt`，其大小为 200 MB，希望将前 100 MB 标记为稀疏区域：

```cmd
fsutil sparse setrange C:\Test\normalfile.txt 0 104857600
```

## 注意事项

- **管理员权限**：大多数 `fsutil` 命令需要在具有管理员权限的命令提示符中运行。右键点击命令提示符图标，选择“以管理员身份运行”。
- **数据丢失**：标记稀疏区域会导致该范围内的原始数据变成零字节，操作前<b>{% span red, 请确认不需要该数据 %}</b>。
- **文件属性**：可使用 `fsutil sparse queryflag` 命令检查文件的稀疏属性。

## 总结

稀疏文件通过只为实际使用的部分分配磁盘空间，实现了节省存储空间和提高存储效率。使用 `fsutil` 命令可以轻松创建和管理稀疏文件，适用于需要创建大文件但不希望实际占用大量磁盘空间的场景。