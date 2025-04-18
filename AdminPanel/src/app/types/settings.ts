export type SendingReportTo = {
  phone_number: string;
  messenger: "whatsapp" | "telegram";
};

export type Setting = {
  setting_id: number;
  setting_name: string;
  setting_description: string;
  format_report: "xlsx";
  type: "filesystem" | "google-drive" | "yandex-disk";
  send_to: SendingReportTo[];
  minute: string;
  hour: string;
  day_of_month: string;
  month: string;
  day_of_week: string;
  deleted: boolean;
  extra: Record<string, any>;
};

export type YandexDiskConfig = {
  token: string;
  shared_folder_name: string;
};

export type GoogleDriveConfig = {
  service_account_json: Record<string, any>;
  shared_folder_name: string;
};