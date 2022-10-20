from nsdf.s3 import S3

import os,sys

from PyQt5 import Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout,QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

 # //////////////////////////////////////////////////////////
class Browser(QTableWidget):
  
	def __init__(self,url="s3://",s3=S3()):
		QTableWidget.__init__(self)
		self.s3=s3
		self.url=None
		self.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.setEditTriggers(QAbstractItemView.NoEditTriggers)
		self.doubleClicked.connect(self.onDoubleClick)
		font = QFont()
		font.setPixelSize(18)
		self.setFont(font)  
		self.resize_cols=True
		self.setUrl(url)

	# goParent
	def goParent(self):
		if self.url=="s3://": return
		self.setUrl("/".join(self.url.split("/")[0:-2])+"/")

	# setUrl
	def setUrl(self,url): 
		print("setUrl",url)
		if not url.startswith("s3://"): return
		if not url.endswith(("/")): url=url+"/"
		self.url=url
		self.setWindowTitle(url)
		self.setCursor(Qt.WaitCursor);
		items=self.s3.listObjects(url)
		self.setCursor(Qt.ArrowCursor);
		self.setRowCount(len(items)+1)
		self.setColumnCount(6)
		R=0
		self.setItem(R, 0, QTableWidgetItem(".."))
		R+=1
		for item in items:
			sub=item['url']
			is_folder=sub.endswith("/")
			self.setItem(R, 0, QTableWidgetItem(sub.split("/")[-2]+"/" if is_folder else sub.split("/")[-1]))
			self.setItem(R, 1, QTableWidgetItem(str(item.get('ETag',''))))
			self.setItem(R, 2, QTableWidgetItem(str(item.get('LastModified',''))))
			self.setItem(R, 3, QTableWidgetItem(str(item.get('Owner',{}).get('DisplayName',''))))
			self.setItem(R, 4, QTableWidgetItem(str(item.get('Size','0'))))
			self.setItem(R, 5, QTableWidgetItem(str(item.get('StorageClass',''))))
			R+=1
   
		if self.resize_cols:
			self.resizeColumnsToContents()
			self.resize_cols=False

	# onDoubleClick
	def onDoubleClick(self):
		R=self.currentIndex().row()
		if R==0: 
			self.goParent()
		else:
			url=self.url + self.item(R,0).text()
			if url.endswith("/"):
				self.setUrl(url)
    

	@staticmethod
	def run(url=None):
		from nsdf.s3 import S3
		app = QApplication(sys.argv)
		browser = Browser(url)
		browser.showMaximized()
		sys.exit(app.exec_())   