import { useParams } from 'react-router-dom'
import PagePlaceholder from '../../components/PagePlaceholder'

// UC-C8: Nhắn tin trực tiếp. REST: chatService.*, realtime: WebSocket
export default function Chat() {
  const { conversationId } = useParams()

  return (
    <PagePlaceholder
      code="UC-C8"
      title="Tin nhắn"
      description={
        conversationId
          ? `Đang mở hội thoại #${conversationId}`
          : 'Trao đổi trực tiếp với nhà tuyển dụng qua WebSocket.'
      }
      todo={[
        'Cột trái: danh sách hội thoại (last_message) + số tin chưa đọc',
        'Khung chat: tải lịch sử (phân trang), gửi/nhận realtime',
        'WebSocket: gửi JWT khi kết nối, tự kết nối lại, gửi lại tin chưa được xác nhận',
        'Trạng thái tin nhắn: đang gửi, đã gửi, đã xem (is_read)',
        'Giới hạn độ dài tin nhắn, hiển thị nội dung an toàn (không render HTML thô)',
      ]}
    />
  )
}
