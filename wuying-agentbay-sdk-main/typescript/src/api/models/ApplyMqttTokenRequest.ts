// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class ApplyMqttTokenRequest extends $dara.Model {
  desktopId?: string;
  sessionToken?: string;
  static names(): { [key: string]: string } {
    return {
      desktopId: 'DesktopId',
      sessionToken: 'SessionToken',
    };
  }

  static types(): { [key: string]: any } {
    return {
      desktopId: 'string',
      sessionToken: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

