import struct

# 定义FAT32文件系统相关的常量
BYTES_PER_SECTOR = 512
BYTES_PER_ENTRY = 32
FILE_NAME = "ZhangYF.docx"
FAT32_IMAGE = "a.img"

# 读取DBR
def getIndex():
    with open(FAT32_IMAGE, "rb") as f:
        dbr = f.read(BYTES_PER_SECTOR)
        # 解析DBR
        bytes_per_sector = struct.unpack_from("<H", dbr[0x0B:0x0D])[0]
        sectors_per_cluster = struct.unpack_from("<B", dbr[0x0D:0x0E])[0]
        reserved_sectors = struct.unpack_from("<H", dbr[0x0E:0x10])[0]
        num_fats = struct.unpack_from("<B", dbr[0x10:0x11])[0]
        sectors_per_fat = struct.unpack_from("<I", dbr[0x24:0x28])[0]
        root_cluster = struct.unpack_from("<I", dbr[0x2C:0x30])[0]

        # 计算根目录起始扇区号
        root_cluster_offset = (root_cluster - 2) * sectors_per_cluster + reserved_sectors + num_fats * sectors_per_fat

        print('Bytes per sector:', bytes_per_sector)
        print('Sectors per cluster:', sectors_per_cluster)
        print('Reserved sector count:', reserved_sectors)
        print('Number of FATs:', num_fats)
        print('Sectors per FAT:', sectors_per_fat)
        print('Root cluster:', root_cluster)
        print('Root cluster offset:', root_cluster_offset)

        return bytes_per_sector, sectors_per_cluster, reserved_sectors, num_fats, sectors_per_fat, root_cluster_offset

# 读取文件目录项
def getStartCluster(bytes_per_sector, sectors_per_cluster, root_cluster_offset):
    with open(FAT32_IMAGE, "rb") as f:
        # 读取根目录的目录项
        f.seek(root_cluster_offset * bytes_per_sector)
        entries = f.read(bytes_per_sector * sectors_per_cluster)
        # 遍历所有目录项，查找对应的文件
        for i in range(0, bytes_per_sector * sectors_per_cluster, BYTES_PER_ENTRY):

            entry = entries[i:i+BYTES_PER_ENTRY]
            name = entry[0:6]
            file_name = FILE_NAME[0:6]
            filename_extension = entry[8:11]
            attributes = struct.unpack("<H", entry[0x0B:0x0D])[0]
            start_cluster_high = struct.unpack("<H", entry[0x14:0x16])[0]
            start_cluster_low = struct.unpack("<H", entry[0x1A:0x1C])[0]
            file_size = struct.unpack("<I", entry[0x1C:0x20])[0]

            if name[0] != 0xE5 and name[0] != 0x00 and attributes != 0x0F:
                # print(name.decode("gbk"))
                if name.decode("gbk").strip() == str.upper(file_name):
                    print("\nfilename_extension:", filename_extension.decode('gbk'))
                    print("attributes:", hex(attributes))
                    print("start_cluster_high:", start_cluster_high)
                    print("start_cluster_low:", start_cluster_low)
                    print("file_size", file_size)
                    break
        return start_cluster_high * 256 + start_cluster_low, file_size


# 获取文件的簇链
def getClusterChain(start_cluster, bytes_per_sector, reserved_sectors):
    # 获取起始簇号
    if start_cluster == 0:
    # 文件大小为0，没有分配簇
        return []
    # 查找簇链
    cluster_chain = [start_cluster]
    with open(FAT32_IMAGE, 'rb') as f:
        fat_offset = reserved_sectors * bytes_per_sector
        while True:
            fat_sector = fat_offset + (start_cluster * 4)
            f.seek(fat_sector)
            fat_entry = f.read(4)
            next_cluster = int.from_bytes(fat_entry, byteorder='little') & 0x0FFFFFFF
            if next_cluster >= 0x0FFFFFF8:
                # 下一个簇号无效，到达文件末尾
                break
            else:
                cluster_chain.append(next_cluster)
                start_cluster = next_cluster
        print("\ncluster_chain:", cluster_chain)
        return cluster_chain

# 获取文件数据并拼接
def getFileData(cluster_chain, bytes_per_sector, sectors_per_cluster, root_cluster_offset, file_size):
    data = b''
    with open(FAT32_IMAGE, 'rb') as f:
        remainder = file_size % (bytes_per_sector * sectors_per_cluster)

        for cluster in cluster_chain:
            sector_offset = root_cluster_offset + (cluster - 2) * sectors_per_cluster
            f.seek(sector_offset * bytes_per_sector)
            if cluster == cluster_chain[len(cluster_chain) - 1]:
                data += f.read(remainder)
            else:
                data += f.read(bytes_per_sector * sectors_per_cluster)
        return data

def compareFiles(file1, file2, file_size):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        while True:
            chunk1 = f1.read(file_size)
            chunk2 = f2.read(file_size)
            if chunk1 != chunk2:
                return False
            elif not chunk1:
                return True

if __name__ == '__main__':

    bytes_per_sector, sectors_per_cluster, reserved_sectors, num_fats, sectors_per_fat, root_cluster_offset = getIndex()

    start_cluster, file_size = getStartCluster(bytes_per_sector, sectors_per_cluster, root_cluster_offset)

    cluster_chain = getClusterChain(start_cluster, bytes_per_sector, reserved_sectors)

    data = getFileData(cluster_chain, bytes_per_sector, sectors_per_cluster, root_cluster_offset, file_size)

    new_filename = 'ZhangYFcopy.docx'
    with open(new_filename, 'ab+') as f:
        f.write(data)

    # 比较两个文件内容是否相同
    if compareFiles(FILE_NAME, new_filename, file_size):
        print('文件内容完全相同')
    else:
        print('文件内容不相同')