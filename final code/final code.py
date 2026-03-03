import threading
import os
import serial
import time
import math
import serial.tools.list_ports
import speech_recognition as sr
import pyaudio
import re
import pyttsx3
GOOGLE_APPLICATION_CREDENTIALS="C:\realecho-67450-bdd4621d1bf5.json"
from google.cloud import translate_v2 as translate


def print_serial_ports_info():
    # 모든 시리얼 포트 목록 가져오기
    ports = serial.tools.list_ports.comports()
    
    # 각 포트의 정보를 출력
    for port in ports:
        print(f"Device: {port.device}")
        print(f"Name: {port.name}")
        print(f"Description: {port.description}")
        print(f"Hardware ID: {port.hwid}")
        print(f"Manufacturer: {port.manufacturer}")
        print(f"Product: {port.product}")
        print(f"Serial Number: {port.serial_number}")
        print(f"Location: {port.location}")
        print(f"Interface: {port.interface}")
        print("-" * 40)

# 함수 호출
print_serial_ports_info()

def find_and_open_ftdi_port(baudrate=115200):
    # 모든 시리얼 포트 목록 가져오기
    ports = serial.tools.list_ports.comports()
    
    # FTDI 제조사의 포트를 찾기
    for port in ports:
        if port.manufacturer and 'FTDI' in port.manufacturer:
            try:
                uart = serial.Serial(port.device, baudrate)
                print(f"Opened FTDI port: {port.device}")
                return uart
            except serial.SerialException as e:
                print(f"Could not open port {port.device}: {e}")
    print("No FTDI ports found.")
    return None

# FTDI 제조사의 포트를 찾아서 열기
uart = find_and_open_ftdi_port()
# uart = serial.Serial('/dev/cu.usbserial-1', 115200)

# robot moving thread 를 위한 두 변수 
state = 0
commandQ = None

time.sleep(2)

def sendCommand(command):
  uart.write(str.encode(command)) 

  while True:
    inputLine = uart.readline().decode("utf-8")
    if len(inputLine) > 0:
        if inputLine.find("ok") > -1:
        #   print("read ok")
          break
        else:
          print("read : ", inputLine)

####################################################################
####################################################################
####################################################################

def checkConnection():
    """
    로봇과 연결되어있는지 확인하는 함수입니다.
    M400 코드를 보낸 후, 0.1초간 리턴을 확인합니다. 
    리턴이 돌아오지 않는다면 로봇과 연결돼있지 않다고 간주하고, 리턴이 돌아온다면 로봇과 연결돼있다고 간주합니다.

    """
    command = "M400\n"
    uart.write(command.encode())
    strt = time.time()
    while True:
        if(time.time() - strt > 0.1):
            return False
        read_data = uart.read()
        if read_data:
            if read_data.decode('utf-8').find("ok") > -1:
                break
            else:
                pass
    return True

# def sendCommand(command):
#     """
#     모듈 내부적으로 로봇에 커맨드를 보내기 위해 사용하는 함수입니다.

#     :param command: string, 보낼 커맨드

#     커맨드를 로봇에 보내고, 리턴이 돌아올 때까지 대기합니다.
#     """
#     uart.write(command.encode())
#     while True:
#         read_data = uart.read()
#         if read_data:
#             if read_data.decode('utf-8').find("ok") > -1:
#                 break
#             else:
#                 pass
#         time.sleep(0.00001)

def sendCommandNoReturn(command):
    """
    모듈 내부적으로 로봇에 커맨드를 보내기 위해 사용하는 함수입니다.

    :param command: string, 보낼 커맨드

    커맨드를 로봇에 보냅니다.
    """
    uart.write(command.encode())

def moveThread():
    """
    로봇이 움직임을 수행하는 동안 다음 python script를 실행할 수 있게 하는 thread 함수입니다. 모듈 하단에서 thread를 활성화합니다. 모듈 내부에서 사용합니다.
    """
    while True:
        global state

        if state == 0:      # 
            global commandQ
            if commandQ != None:
                state = 1   # 움직임을 시작하기 앞서 state 를 1 로 만들어 움직이고 있음을 변수로 알린다
                sendCommand(commandQ)
                sendCommand("M400\n")
                commandQ = None # commandQ를 None으로 바꿔서 다음 루프에 처리해야 할 일이 없음을 알린다.
                state = 0   # 움직임이 종료된 이후 state를 0으로 바꾸어 움직이지 않고 있음을 알린다.
        else:
            pass
        time.sleep(0.00001)
    
def isMoving():
    """
    로봇이 움직이고 있는지 반환하는 함수입니다. moveG0, moveG1, moveThread 에서 사용합니다.

    :return: state(boolean)
    
    """
    global state
    try:
        return state
    except:
        return 1

def checkXYZ(x,y,z):
    """
    지정된 x, y, z 좌표로 로봇이 움직일 수 있는지(G0) 검사하는 함수입니다.

    :param x: float, x 좌표
    :param y: float, y 좌표
    :param z: float, z 좌표

    :return: int, 참이면 1, 거짓이면 0을 리턴합니다.
    """
    leng = math.sqrt(x*x + y*y)
    if(leng <=213.44 and z >=2.182):
        if(z<=9.066):
            if(not (leng > 61 + math.pow((55*55 -(z-30)**2),(0.5)))):
                #print('first err')
                return 0
        elif(z<=100.1):
            if(not (leng > math.pow((152**2-(z-147)**2),(0.5))+48)):
                #print('second err')
                return 0
        else:
            if(not (leng > math.pow((3600 - (z-148)**2),(0.5))+153.5)):
                #print('third err')
                return 0
    elif(leng <= 224.566 and z <=3.241):
        if(not (leng > math.pow((144**2 - (z+138)**2),(0.5))+81)):
            #print('fourth err')
            return 0
    else:
        if(not ((leng < (16500+100*z)/17) and ((leng-228)**2+(z+4)**2 <150**2))):
            #print('fifth err')
            return 0
    
    if( y <0):
        ix = (-1*y)/leng
        # print("ix: ",ix)
        if 0.98 < ix:
            return 0

    # print('cango')    
    return 1
    
def moveG0(x, y, z, wait = True): # wait 이라는 새 파라미터. True면 기존대로 동작, False면 thread로 동작
    """
    로봇의 G0 움직임을 수행하는 함수입니다.
    :param wait: boolean, 로봇의 움직임이 끝나고 return을 쏠 때까지 기다릴 것인지 아닌지에 대한 매개변수입니다. True일 시 기다립니다.

    로봇의 G0 움직임은 빠른 이동으로, 로봇이 가능한 빠르게 움직입니다.
    """ 
    #y -=30
    z -= 30 
    send = 0
    if(checkXYZ(x,y,z)==1):
        send = 1
    

    global commandQ
    command = "G0 X" + str(x) + " Y" + str(y) + " Z" + str(z) + "\n"
    
    time.sleep(0.00001)
    global state
    
    if state == 0 and send ==1:  # 현재 움직임이 없다면
        if wait == True:    # 기존대로 동작
            state = 1
            sendCommand(command)
            sendCommand("M400\n")
            sendCommand("M204 P50" + "\n")
            state = 0

        elif wait == False: # 새 동작
            commandQ = command
    elif state == 1:           # 현재 움직임이 있다면 아무 동작 X
        send = 2
        pass
    time.sleep(0.00001)
    return send         # 범위, 움직이기 모두 되면 1, 범위는 되는데 움직이기는 안되면 2, 범위 안되면 0

def moveG1(x, y, z, wait = True): # wait 이라는 새 파라미터. True면 기존대로 동작, False면 thread로 동작 
    """
    로봇의 G1 움직임을 수행하는 함수입니다.

    :param wait: boolean, 로봇의 움직임이 끝나고 return을 쏠 때까지 기다릴 것인지 아닌지에 대한 매개변수입니다. True일 시 기다립니다.

    로봇의 G1 움직임은 직선 이동으로, 로봇이 직선을 그리며 움직입니다.
    """ 

    #y -= 30
    z -= 30
    send = 0
    if(checkXYZ(x,y,z)==1):
        send = 1
    

    global commandQ
    command = "G1 X" + str(x) + " Y" + str(y) + " Z" + str(z) + "\n"
    
    time.sleep(0.00001)
    global state
    
    if state == 0 and send ==1:  # 현재 움직임이 없다면
        if wait == True:    # 기존대로 동작
            state = 1
            sendCommand(command)
            sendCommand("M400\n")
            sendCommand("M204 P50" + "\n")
            
            state = 0

        elif wait == False: # 새 동작
            commandQ = command
    elif state == 1:           # 현재 움직임이 있다면 아무 동작 X
        send = 2
        pass
    time.sleep(0.00001)
    return send         # 범위, 움직이기 모두 되면 1, 범위는 되는데 움직이기는 안되면 2, 범위 안되면 0

def pumpOn():
    command = "M1400 A1023" + "\n"
    sendCommand(command)

def pumpOnGripper():
    # A623으로 바꾸면 suction의 세기도 변함
    command = "M1400 A623" + "\n"
    sendCommand(command)

def pumpOff():
    command = "M1400 A0" + "\n"
    sendCommand(command)

def pump(power):
    command = "M1400 A" + str(power) + "\n"
    sendCommand(command)

def valveOn():
    command = "M1401 A1" + "\n"
    sendCommand(command)

def valveOff():
    command = "M1401 A0" + "\n"
    sendCommand(command)

def suctionOn():
    """
    로봇의 석션 모듈을 On으로 설정합니다
    """
    valveOff()
    pumpOn()

def suctionOff():
    """
    로봇의 석션 모듈을 Off로 설정합니다
    """
    pumpOff()
    valveOn()
    time.sleep(0.3)
    valveOff()

def gripper(state):
    """
    로봇의 그리퍼 모듈을 설정합니다.
    
    :param state: int, 0 - 대기, 1 - 열림, 2 - 닫기

    """
    if state == 0:
        pumpOff()
        valveOn()
        time.sleep(0.3)
        valveOff()
    elif state == 1:
        valveOff()
        pumpOnGripper()
    elif state == 2:
        valveOn()
        pumpOnGripper()

def set_current_position():
    sendCommand("M1500 B4\n")

def moveAngle(a,b,c):
    """
    로봇을 축의 각도로 움직입니다.

    :param a: float, angle a
    :param b: float, angle b
    :param c: float, angle c
    
    """
    command = "M1005 A" + str(a) + " B" + str(b) + " C" + str(c) + "\n"
    sendCommand(command)
    sendCommand("M400\n")

def moveAngle_noM400(a,b,c):
    command = "M1005 A" + str(a) + " B" + str(b) + " C" + str(c) + "\n"
    sendCommand(command)

def moveZ0_M400(z):
    command = "G0 Z" + str(z) + "\n"
    sendCommand(command)
    sendCommand("M400\n")

def moveZ0(z):
    command = "G0 Z" + str(z) + "\n"
    sendCommand(command)

def extract_floats(text):
    """
    regex을 이용하여 로봇의 return에서 float값을 반환하는 함수입니다. 모듈 내부에서 사용합니다.

    :param text: string, 로봇에서 온 리턴값을 넣습니다.

    :return: list(float), text에서 float을 찾아(+,- 구분) 리스트로 반환합니다.
    """

    floats = []
    current_number = ""

    for char in text:
        if char.isdigit() or char in ".+-":
            current_number += char
        else:
            if current_number:
                try:
                    floats.append(float(current_number))
                except ValueError:
                    pass  # Ignore invalid format
                current_number = ""

    if current_number:
        try:
            floats.append(float(current_number))
        except ValueError:
            pass

    return floats

def getLoc():
    """
    로봇 팔의 현재 좌표를 구하는 함수입니다.

    :return: tuple (x(float), y(float), z(float)) , 로봇 좌표 (x,y,z)를 tuple로 반환합니다.
    
    """
    uart.write("M1008 A3\n".encode())
    read_data = None

    while True:
        read_data = uart.readline().decode("utf-8")
        if len(read_data) > 0:
            if read_data.find("ok") > -1:
                break
            else:
                a = extract_floats(read_data)
                pass
    return a

def getLocCanNull():
    """
    로봇 팔의 현재 좌표를 구하는 함수입니다.

    :return: tuple (x(float), y(float), z(float)) , 로봇 좌표 (x,y,z)를 tuple로 반환합니다.
    
    """
    uart.write("M1008 A3\n".encode())
    read_data = None
    cnTime = time.time()
    while True:
        read_data = uart.read()
        if(time.time() - cnTime > 0.01):
            return None
        if read_data:
            if read_data.decode('utf-8').find("ok") > -1:
                break
            else:
                if(time.time() - cnTime > 0.01):
                    return None

    return extract_floats(read_data.decode('utf-8'))



def getDeg():
    """
    로봇 축들의 각도(엔코더 값)를 받는 함수입니다.
    
    :return: tuple (a(float), b(float), c(float)) , 로봇 각 축의 엔코더 값을 tuple로 반환합니다.
    """
    uart.write("M1008 A2\n")
    read_data = None
    while True:
        read_data = uart.read()
        if read_data:
            if read_data.decode('utf-8').find("ok") > -1:
                break
            else:
                pass
    return extract_floats(read_data.decode('utf-8'))

def freeMod():
    """
    로봇 모터의 힘을 풉니다. 사용자가 로봇을 자유롭게 움직일 수 있게 합니다.
    """
    sendCommand("M84\n")

def unsetFreeMod():
    """
    로봇 모터에 힘을 가합니다. 사용자가 로봇을 자유롭게 움직일 수 없게 합니다.
    """
    sendCommand("M17\n")

# def moduleCheckAble(enable):
#     """

#     """
#     sendCommand("M1600 D" + str(enable) + "\n")

# _thread.start_new_thread(moveThread,())

####################################################################
####################################################################
####################################################################
####################################################################

# //  떼고 싶기 때문 버튼을 꾹 누른다
# // M1700 B1 24v 흘림
# // M1301 magnet on

# // 일정 시간 -> 2sec
# // M1300 magnet off
# // M1700 B0 0v

def head_24V_on():
    sendCommand("M1700 B1\n")

def head_24V_off():
    sendCommand("M1700 B0\n")

#오래 사용시 전자석 발열 주의
def head_module_detach():
    head_24V_on()
    time.sleep(0.5)
    sendCommand("M1301\n")

def reset_head_magnet():
    sendCommand("M1300\n")
    head_24V_off()


def find_point_on_line_min(x1, y1, z, B):
    """
    주어진 점 (x1, y1)에서 거리 B만큼 떨어진 y = Ax 위의 점 (x2, y2)를 구합니다.
    
    Parameters:
    x1 (float): 주어진 점의 x 좌표
    y1 (float): 주어진 점의 y 좌표 (y1 = Ax1)
    B (float): 두 점 사이의 거리
    
    Returns:
    tuple: (x2, y2) 점 (x2는 x1보다 작습니다)
    """
    if x1 == 0:
        # x1이 0인 경우
        x2 = 0
        y2 = y1 - B if y1 > 0 else y1 + B
    else:
        # 일반적인 경우
        A = y1 / x1
        delta_x = B / math.sqrt(1 + A**2)

        sign = int(math.copysign(1, x1))
        
        x2 = x1 - sign*delta_x
        y2 = A * x2
    
    return [x2, y2, z]

def find_point_on_line_max(x1, y1, z, B):
    """
    주어진 점 (x1, y1)에서 거리 B만큼 떨어진 y = Ax 위의 점 (x2, y2)를 구합니다.
    
    Parameters:
    x1 (float): 주어진 점의 x 좌표
    y1 (float): 주어진 점의 y 좌표 (y1 = Ax1)
    B (float): 두 점 사이의 거리
    
    Returns:
    tuple: (x2, y2) 점 (x2는 x1보다 큽니다)
    """
    if x1 == 0:
        # x1이 0인 경우
        x2 = 0
        y2 = y1 + B if y1 > 0 else y1 - B
    else:
        # 일반적인 경우
        A = y1 / x1
        delta_x = B / math.sqrt(1 + A**2)

        sign = int(math.copysign(1, x1))
        
        x2 = x1 + sign * delta_x
        y2 = A * x2
    
    return [x2, y2, z]

def find_point_distance_of_A_from_origin(x1, y1, A):
    """
    주어진 점 (x1, y1)을 지나는 일차함수에서 원점으로부터 거리 A만큼 떨어진 점 (x2, y2)를 구합니다.
    
    Parameters:
    x1 (float): 주어진 점의 x 좌표
    y1 (float): 주어진 점의 y 좌표
    A (float): 원점으로부터의 거리
    
    Returns:
    tuple: 원점에서 A만큼 떨어진 점 (x2, y2)
    """
    if x1 == 0:
        # x1이 0인 경우
        x2 = 0
        y2 = A if y1 > 0 else -A
    else:
        # 일반적인 경우
        m = y1 / x1
        
        # x2 계산
        x2 = A / math.sqrt(1 + m**2)
        
        # x1과 동일한 부호를 가지도록 x2 조정
        if x1 < 0:
            x2 = -x2
        
        # y2 계산
        y2 = m * x2
    
    return [x2, y2]

# head_module_detach()

#########################################################
#########################################################
#########################################################

def getState():
    """
    로봇 팔의 현재 좌표를 구하는 함수입니다.

    :return: tuple (x(float), y(float), z(float)) , 로봇 좌표 (x,y,z)를 tuple로 반환합니다.
    
    """
    uart.write("M1600\n".encode())
    read_data = None
    output = ""

    while True:
        read_data = uart.readline().decode("utf-8")
        if len(read_data) > 0:
            if read_data.find("ok") > -1:
                break
            else:
                print(read_data)
                output = read_data
                pass
    return output

def extract_module_status(data):
    # 데이터 문자열을 공백으로 분할
    parts = data.split()
    
    # 각 부분을 검사하여 module_status를 찾기
    for part in parts:
        if part.startswith("current_module:"):
            # module_status의 값을 추출하여 반환
            return part.split(":")[1]
    
    # module_status가 없으면 None 반환
    return None

def ATC_module_detach(ATC_home):
    current_position = getLoc()
    distance_ATC = math.sqrt(ATC_home[0]**2 + ATC_home[1]**2)
    point_1 = find_point_distance_of_A_from_origin(current_position[0], current_position[1], distance_ATC+50)
    moveG1(point_1[0], point_1[1], ATC_home[2] + 30) # ATC위치와 같은 반경 안에 있는 위치로 이동
    point_3 = find_point_distance_of_A_from_origin(ATC_home[0], ATC_home[1],distance_ATC+50)
    moveG1(point_3[0], point_3[1], ATC_home[2] + 30)
    moveG1(ATC_home[0], ATC_home[1], ATC_home[2] + 30) # ATC위치에서 z +30 위치 이동
    moveG1(ATC_home[0], ATC_home[1], ATC_home[2]) # ATC위치로 이동
    head_module_detach() # 모듈 탈착
    time.sleep(1)
    point_2 = find_point_on_line_min(ATC_home[0], ATC_home[1], ATC_home[2], 30) # 30mm 뒤로
    moveG1(point_2[0], point_2[1], ATC_home[2]) # ATC위치에서 뒤로 이동
    reset_head_magnet() # 마그넷 리셋

    # point_1 = find_point_on_line_max(current_position[0], current_position[1], current_position[2], 30)
    # point_ATC = find_point_on_line_min(ATC_home[0], ATC_home[1], ATC_home[2], 30)
    # point_max = find_point_on_line_max(ATC_home[0], ATC_home[1], ATC_home[2], 30)

def ATC_module_attach(ATC_home):
    head_24V_off()
    current_position = getLoc()
    point_1 = find_point_on_line_min(ATC_home[0], ATC_home[1], ATC_home[2], 30) # 30mm 뒤로
    distance_ATC = math.sqrt(point_1[0]**2 + point_1[1]**2)
    point_2 = find_point_distance_of_A_from_origin(current_position[0], current_position[1], distance_ATC)
    moveG1(point_2[0], point_2[1], ATC_home[2]) # ATC위치 보다 작은 반경으로 이동
    moveG1(point_1[0], point_1[1], ATC_home[2]) # ATC위치 뒤로 이동
    moveG1(ATC_home[0], ATC_home[1], ATC_home[2]) # ATC위치로 이동
    moveG1(ATC_home[0], ATC_home[1], ATC_home[2]+30) # ATC위치에서 30mm 위로 이동

#######################################################################################################################
#LASER#################################################################################################################
#######################################################################################################################

def laser_power(power):
    if power == -1:
        head_24V_off()
        sendCommand("M1601 S0\n")
    elif power == 0:
        # head_24V_on()
        sendCommand("M1601 S0\n")
    else:
        # head_24V_on()
        command = "M1601 S" + str(power) + "\n"
        sendCommand(command)


#######################################################################################################################
#######################################################################################################################
#######################################################################################################################

import openpyxl
from openpyxl import Workbook
import os
from datetime import datetime

def extract_gganada_values(data):
    values = []
    lines = data.split('\n')  # 각 줄로 분할
    for line in lines:
        if 'gganada' in line:
            parts = line.split('=')
            if len(parts) == 2:
                value = parts[1].strip()
                try:
                    values.append(float(value))  # 숫자 값으로 변환하여 리스트에 추가
                except ValueError:
                    pass  # 변환 실패 시 무시
    return values

def record_status_to_excel(filename):
    # 워크북 생성 또는 기존 워크북 열기
    try:
        workbook = openpyxl.load_workbook(filename)
        sheet = workbook.active
    except FileNotFoundError:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Status"])  # 첫 번째 행에 헤더 추가

    # 상태 확인 및 엑셀에 기록
    state = getState()
    module_status = extract_gganada_values(state)
    print(module_status)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append([timestamp, "OK", module_status[0]])
    workbook.save(filename)
    print("Recorded 'OK' to Excel.")

ATC_home = [0, 208, -8]

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "status_record.xlsx")


###############################################################################################################################################################################################
###############################################################################################################################################################################################
###############################################################################################################################################################################################
shiftsum = 0
shift = 0
count = 0
alpha_width = { 'A': 23.220, 'B': 19.344, 'C': 21.273, 'D': 21.670, 'E': 16.898, 'F': 16.381, 'G': 22.858, 'H': 19.620, 'I': 10.129, 'J': 12.092, 'K': 20.533, 'L': 16.226, 'M': 22.841,
          'N': 19.568, 'O': 23.823, 'P':16.778, 'Q': 24.340, 'R': 21.222, 'S': 19.775, 'T': 21.739, 'U': 19.689, 'V': 23.220, 'W': 31.712, 'X': 21.842, 'Y': 21.497, 'Z': 20.016,
          'a': 16.347, 'b': 16.933, 'c': 15.606, 'd': 16.933, 'e': 17.467, 'f': 12.368, 'g': 16.933,'h': 16.089,'i': 3.652,'j': 10.249,'k': 17.329,'l': 3.238,'m': 28.077,
          'n': 16.089,'o': 17.759,'p': 16.933,'q': 16.933,'r': 12.006,'s': 15.038,'t': 12.109,'u': 16.089,'v': 18.776,'w': 25.907,'x': 18.810,'y': 18.776,'z': 15.537}

word_flag = 0
line_shift = 0
unknown = 0


# 단어의 길이를 계산하는 함수
def calculate_word_length(word):
    return sum(alpha_width.get(char, 20) for char in word)  # 알파벳 딕셔너리에서 길이 가져오기, 기본값 5mm

def split_sentence_based_on_width(sentence, max_length=280):
    # 입력된 문장을 띄어쓰기를 기준으로 단어 리스트로 분리
    words = sentence.split()
    # 결과를 저장할 리스트 초기화
    lines = []
    # 현재 라인의 누적 길이와 단어들을 저장할 임시 변수 초기화
    current_line = ""
    current_length = 0

    for word in words:
        # 현재 단어의 길이 계산
        word_length = calculate_word_length(word) + calculate_word_length(" ")  # 공백 추가

        # 현재 라인의 길이와 다음 단어 길이 합이 최대 길이 초과 여부 확인
        if current_length + word_length <= max_length:
            # 초과하지 않으면 현재 라인에 단어 추가
            current_line += word + " "
            current_length += word_length
        else:
            # 초과하면 현재 라인을 결과 리스트에 추가하고, 새로운 라인 시작
            lines.append(current_line.strip())
            current_line = word + " "
            current_length = word_length

    # 마지막 라인도 결과에 추가
    if current_line:
        lines.append(current_line.strip())

    return lines


def parse_gcode(file_path):
    global shiftsum

    with open(file_path, 'r') as file:
        lines = file.readlines()
    shiftsum += shift

    for line in lines:
        # G0 또는 G1으로 시작하는 명령어를 찾습니다.
        if line.startswith('G00') or line.startswith('G01') or line.startswith('G02') or line.startswith('G03'):
            command = line.split()[0]
            x, y, z = 0, 0, 0

            # X, Y, Z 좌표를 찾습니다.
            for part in line.split():
                if part.startswith('X'):
                        x = float(part[1:]) + startpoint - shiftsum - 2
                        print(shiftsum)
                elif part.startswith('Y'):
                    y = float(part[1:]) + line_shift
                elif part.startswith('Z'):
                    z = float(part[1:])

            # G0 또는 G1에 따라 moveG0 또는 moveG1 함수를 호출합니다.
            if command == 'G00' or command == 'G02' or command == 'G03':
                moveG0(x, y, z, wait = True)
            elif command == 'G01':
                moveG1(x, y, z, wait = True)


######영단어에 맞는 G-code 파일 불러옴######
def select_word(word):
    global shift

    match word:
        case 'A'|'a' :
            if(word == 'A'):
                shift = 23.220
                parse_gcode('G:\gcode\A.ngc')
            else:
                shift = 16.347
                parse_gcode('G:\gcode\A_small.ngc')
            

        case 'B'|'b':
            if(word == 'B'):
                shift = 19.344
                parse_gcode('G:\gcode\B.ngc')
            else:
                shift = 16.933
                parse_gcode('G:\gcode\B_small.ngc')
            

        case 'C'|'c':
            if(word == 'C'):
                shift = 21.273
                parse_gcode('G:\gcode\C.ngc')
            else:
                shift = 15.606
                parse_gcode('G:\gcode\C_small.ngc')
            

        case 'D'|'d':
            if(word == 'D'):
                shift = 21.670
                parse_gcode('G:\gcode\D.ngc')
            else:
                shift = 16.933
                parse_gcode('G:\gcode\D_small.ngc')
            

        case 'E'|'e':
            if(word == 'E'):
                shift = 16.898
                parse_gcode('G:\gcode\E.ngc')
            else:
                shift = 17.467
                parse_gcode('G:\gcode\E_small.ngc')
            

        case 'F'|'f':
            if(word == 'F'):
                shift = 16.381
                parse_gcode('G:\gcode\F.ngc')
            else:
                shift = 12.368
                parse_gcode('G:\gcode\F_small.ngc')
            
        
        case 'G'|'g':
            if(word == 'G'):
                shift = 22.858
                parse_gcode('G:\gcode\G.ngc')
            else:
                shift = 16.933
                parse_gcode('G:\gcode\G_small.ngc')
            
        
        case 'H'|'h':
            if(word == 'H'):
                shift = 19.620
                parse_gcode('G:\gcode\H.ngc')
            else:
                shift = 16.089
                parse_gcode('G:\gcode\H_small.ngc')
            
        
        case 'I'|'i':
            if(word == 'I'):
                shift = 10.129
                parse_gcode('G:\gcode\I.ngc')
            else:
                shift = 3.652
                parse_gcode('G:\gcode\I_small.ngc')
            
        
        case 'J'|'j':
            if(word == 'J'):
                shift = 12.092
                parse_gcode('G:\gcode\J.ngc')
            else:
                shift = 10.249
                parse_gcode('G:\gcode\J_small.ngc')
            
    
        case 'K'|'k':
            if(word == 'K'):
                shift = 20.533
                parse_gcode('G:\gcode\K.ngc')
            else:
                shift = 17.329
                parse_gcode('G:\gcode\K_small.ngc')
            
        
        case 'L'|'l':
            if(word == 'L'):
                shift = 16.226
                parse_gcode('G:\gcode\L.ngc')
            else:
                shift = 3.238
                parse_gcode('G:\gcode\L_small.ngc')
            
        
        case 'M'|'m':
            if(word == 'M'):
                shift = 22.841
                parse_gcode('G:\gcode\M.ngc')
            else:
                shift = 28.077
                parse_gcode('G:\gcode\M_small.ngc')
            
        
        case 'N'|'n':
            if(word == 'N'):
                shift = 19.568
                parse_gcode('G:\gcode\\N.ngc')
            else:
                shift = 16.089
                parse_gcode('G:\gcode\\N_small.ngc')
            
        
        case 'O'|'o':
            if(word == 'O'):
                shift = 23.823
                parse_gcode('G:\gcode\O.ngc')
            else:
                shift = 17.759
                parse_gcode('G:\gcode\O_small.ngc')
            
        
        case 'P'|'p':
            if(word == 'P'):
                shift = 16.778
                parse_gcode('G:\gcode\P.ngc')
            else:
                shift = 16.933
                parse_gcode('G:\gcode\P_small.ngc') 
            
        
        case 'Q'|'q':
            if(word == 'Q'):
                shift = 24.340
                parse_gcode('G:\gcode\Q.ngc')
            else:
                shift = 16.933
                parse_gcode('G:\gcode\Q_small.ngc')
            
        
        case 'R'|'r':
            if(word == 'R'):
                shift = 21.222
                parse_gcode('G:\gcode\R.ngc')
            else:
                shift = 12.006
                parse_gcode('G:\gcode\R_small.ngc')
            
        
        case 'S'|'s':
            if(word == 'S'):
                shift = 19.775
                parse_gcode('G:\gcode\S.ngc')
            else:
                shift = 15.038
                parse_gcode('G:\gcode\S_small.ngc')
            
        
        case 'T'|'t':
            if(word == 'T'):
                shift = 21.739
                parse_gcode('G:\gcode\T.ngc')
            else:
                shift = 12.109
                parse_gcode('G:\gcode\T_small.ngc')
            
        
        case 'U'|'u':
            if(word == 'U'):
                shift = 19.689
                parse_gcode('G:\gcode\\U.ngc')
            else:
                shift = 16.089
                parse_gcode('G:\gcode\\U_small.ngc')
            
        
        case 'V'|'v':
            if(word == 'V'):
                shift = 23.220
                parse_gcode('G:\gcode\V.ngc')
            else:
                shift = 18.776
                parse_gcode('G:\gcode\V_small.ngc')
            
        
        case 'W'|'w':
            if(word == 'W'):
                shift = 31.712
                parse_gcode('G:\gcode\W.ngc')
            else:
                shift = 25.907
                parse_gcode('G:\gcode\W_small.ngc')
            
        
        case 'X'|'x':
            if(word == 'X'):
                shift = 21.842
                parse_gcode('G:\gcode\X.ngc')
            else:
                shift = 18.810
                parse_gcode('G:\gcode\X_small.ngc')
            
        
        case 'Y'|'y':
            if(word == 'Y'):
                shift = 21.497
                parse_gcode('G:\gcode\Y.ngc')
            else:
                shift = 18.776
                parse_gcode('G:\gcode\Y_small.ngc')
            
        
        case 'Z'|'z':
            if(word == 'Z'):
                shift = 20.016
                parse_gcode('G:\gcode\Z.ngc')
            else:
                shift = 15.537
                parse_gcode('G:\gcode\Z_small.ngc')
        
        case _:
            global shiftsum
            shiftsum += 11


####################################################################################
moveG0(0,180,25,True) #원점 이동

######음성인식된 한국어 영어로 변환 with google transation api######
def translate_text(text, target_language='en'):
    # 클라이언트 초기화
    translate_client = translate.Client()

    # 번역 수행
    result = translate_client.translate(text, target_language=target_language)
    return result['translatedText']

######텍스트 speaking with pyttsx3######
def configure_and_speak(text):
    engine = pyttsx3.init()

    #속도 조절
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate -60)

    #볼륨 조절
    volume = engine.getProperty('volume')
    engine.setProperty('volume', 1.0)
    engine.say(text)
    engine.runAndWait()

while 1:
    ######단어 or 문장 선택######
    while True:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            configure_and_speak("단어와 문장 중 어떤 것을 학습하시겠습니까?")
            audio = r.listen(source)

        try:
            answer = r.recognize_google(audio, language='ko')
            print("사용자 응답:", answer)
                    
            if answer == '단어':
                word_flag = 0
                break
            elif answer == '문장':
                word_flag = 1
                break
            else:
                configure_and_speak("죄송합니다. '단어' 또는 '문장'으로 응답해 주세요.")
                    

        except sr.UnknownValueError:
            configure_and_speak("인식에 실패하였습니다. 다시 말해주세요.")
            continue

        except sr.RequestError as e:
            configure_and_speak("인식에 실패하였습니다. 다시 말해주세요.")
            continue

    ######단어 인식######
    global text #text 담을 공간 변수

    if word_flag == 0:
        while True:
            with sr.Microphone() as source:
                configure_and_speak("단어를 말해주세요.")
                audio = r.listen(source)

            try:
                text = r.recognize_google(audio, language='ko')
                print(f"입력 텍스트: {text}")
                break

            except sr.UnknownValueError:
                configure_and_speak("인식에 실패하였습니다. 다시 말해주세요.")
                continue

            except sr.RequestError as e:
                configure_and_speak("인식에 실패하였습니다. 다시 말해주세요.")
                continue

    ######문장 인식#######
    elif word_flag == 1:
        while True:
            with sr.Microphone() as source:
                configure_and_speak("문장을 말해주세요.")
                audio = r.listen(source)

            try:
                text = r.recognize_google(audio, language='ko')
                print(f"입력 텍스트: {text}")
                break

            except sr.UnknownValueError:
                configure_and_speak("인식에 실패하였습니다. 다시 말해주세요.")
                continue

            except sr.RequestError as e:
                configure_and_speak("인식에 실패하였습니다. 다시 말해주세요.")
                #print('요청실패 : {0}'.format(e))
                continue



    translated_text = translate_text(text, target_language='en')

    print(f"한글 텍스트: {text} /번역 결과: {translated_text}")
    count = 0

    configure_and_speak(f"영어로 {text} {translated_text}입니다.")

    ######단어 15글자 이상 OR 이하 case######
    if word_flag == 0:
        alpha_count = len(translated_text)
        alpha_count /= 2
        startpoint = 0
        print(alpha_count)

        if 1 <= alpha_count <= 8:
            startpoint = 13 * alpha_count
            for unknown in translated_text:
                if(count == 0):
                    if(unknown.islower()):
                        unknown = unknown.upper()
                count+=1
                select_word(unknown)
        else:
            translated_text = split_sentence_based_on_width(translated_text, max_length=280)

            for idx, line in enumerate(translated_text):
                print(f"Line {idx + 1}: {line}")
                ######음성인식된 영어 한 글자씩 분할, 대소문자 구분 및 띄어쓰기 구분하여 출력######
                for unknown in line:
                    print("성공")
                    if(count == 0):
                        if(unknown.islower()):
                            unknown = unknown.upper()
                    count+=1
                    startpoint = 120 #시작 포인트는 문장 작성시 항상 140 앞에서 시작하도록 
                    
                    select_word(unknown)

                line_shift += 30 #25 shifting
                shiftsum = 0 #다음줄 실행 시 shiftsum 초기화

    ######문장 case#######
    elif word_flag == 1:
        translated_text = split_sentence_based_on_width(translated_text, max_length=280)

        for idx, line in enumerate(translated_text):
            print(f"Line {idx + 1}: {line}")
            ######음성인식된 영어 한 글자씩 분할, 대소문자 구분 및 띄어쓰기 구분하여 출력######
            for unknown in line:
                print("성공")
                if(count == 0):
                    if(unknown.islower()):
                        unknown = unknown.upper()
                count+=1
                startpoint = 120 #시작 포인트는 문장 작성시 항상 140 앞에서 시작하도록 
                
                select_word(unknown)

            line_shift += 30 #25 shifting
            shiftsum = 0 #다음줄 실행 시 shiftsum 초기화



    ######마지막 부분 한번 더 소리내어 읽기######
    configure_and_speak(f"{text}")
    configure_and_speak(f"{translated_text}")


    ######원점 이동######
    moveG0(0,180,25,True) 


    ######프로그램 재실행 or 종료#######
    while True:
        configure_and_speak("다시 학습하시겠습니까?")
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source)
            try:
                answer = r.recognize_google(audio, language='ko')
                print("사용자 응답:", answer)
                
                if answer == '네':
                    shiftsum = 0 # 글자 시프트 초기화
                    break  # "네"일 경우 질문 루프 탈출하고 다음 단어 입력으로 이동
                elif answer == '아니요':
                    exit_program = True
                    configure_and_speak("프로그램이 종료되었습니다.")
                    break  # "아니요"일 경우 질문 루프 탈출 및 메인 루프 종료
                else:
                    configure_and_speak("죄송합니다. '네' 또는 '아니요'로 응답해 주세요.")
            
            except sr.UnknownValueError:
                configure_and_speak("인식에 실패하였습니다. 다시 말씀해 주세요.")
            
            except sr.RequestError:
                configure_and_speak("음성 인식에 문제가 발생했습니다.")
        
        if 'exit_program' in locals() and exit_program:
            break

    if 'exit_program' in locals() and exit_program:
        break
        
            
        


