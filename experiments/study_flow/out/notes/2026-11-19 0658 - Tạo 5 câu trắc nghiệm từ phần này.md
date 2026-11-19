# Tạo 5 câu trắc nghiệm từ phần này

## Trắc nghiệm · cheatsheet.pdf (Trang 1)

_Chọn phát biểu đúng và đầy đủ nhất._

1. Trong lớp CharLinkedList, hàm addFirst thực hiện thao tác nào để chèn phần tử vào đầu danh sách?
   - A. Tạo nút mới và đặt nó làm head, không cần cập nhật next
   - B. Tạo nút mới và đặt nó làm next của head
   - C. Tạo nút mới, đặt next của nó là head, rồi cập nhật head thành nút mới ✓
   - D. Tạo nút mới và đặt nó làm tail của danh sách
   > void addFirst(char d){ Node n=new Node(d); n.next=head; head=n; }

2. Trong hàm đệ quy tính luỹ thừa n^k, điều kiện nào là cơ sở dừng (base case)?
   - A. n == 0
   - B. n < 0
   - C. k > 0
   - D. k == 0 ✓
   > static int recur(int n,int k){ if(k==0) return 1; return n*recur(n,k-1); }

Nguồn: cheatsheet.pdf · trang 1

Lưu lúc 2026-11-19 06:58
